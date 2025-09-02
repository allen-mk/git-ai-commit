import asyncio
import os
import stat
import click
from rich.console import Console
from rich.panel import Panel
from rich.status import Status

# 导入 collectors 和 providers 以注册它们
import core.collectors
import core.llm.providers

from config.logic import load_and_merge_configs
from config.models import Config
from core.pipeline import CommitMessageGenerator
from utils.errors import AICommitException
from utils.logger import setup_logger, logger
from utils.git import is_git_repository, has_staged_changes, commit


HOOK_SCRIPT = """#!/bin/sh
# aicommit git hook. Managed by aicommit.

# The commit message file is passed as the first argument.
COMMIT_MSG_FILE="$1"

# The source of the commit message is the second argument.
COMMIT_SOURCE="$2"

# Call the generator and pass along the git hook arguments.
# The command will internally decide whether to run.
exec aicommit generate --from-hook "$COMMIT_MSG_FILE" "$COMMIT_SOURCE"
"""


def apply_cli_overrides(config: Config, provider: str, model: str, template: str) -> Config:
    """将CLI选项应用于加载的配置"""
    if provider:
        config.model.provider = provider
        logger.info(f"使用 provider 覆盖配置: {provider}")
    if model:
        config.model.name = model
        logger.info(f"使用 model 覆盖配置: {model}")
    if template:
        config.formatter.template = template
        logger.info(f"使用 template 覆盖配置: {template}")
    return config


async def run_generation(config: Config) -> str:
    """
    初始化并运行提交信息生成流水线
    """
    pipeline = CommitMessageGenerator(config)
    return await pipeline.generate()


@click.group(invoke_without_command=True)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="启用详细日志记录以进行调试",
)
@click.pass_context
def cli(ctx, verbose: bool):
    """
    AI 驱动的 Git 提交信息生成器。

    如果未指定子命令，则默认运行 'generate'。
    """
    # 设置日志级别
    setup_logger(log_level="DEBUG" if verbose else "INFO")

    # 将 verbose 状态传递给子命令
    ctx.obj = {'verbose': verbose}

    if ctx.invoked_subcommand is None:
        # 在没有子命令时，显式调用 generate
        # 注意: 这种方式下 generate 的参数需要从 ctx.params 获取，或者重新解析
        # 为了简单起见，我们让用户明确运行 `aicommit generate` 或依赖默认行为
        # Click v8+ 会自动处理参数传递
        ctx.invoke(generate)


@cli.command("generate")
@click.option(
    "-c", "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False),
    help="自定义配置文件的路径",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="生成提交信息但不应用它",
)
@click.option(
    "--no-overwrite",
    is_flag=True,
    default=None,  # Default to None to distinguish from False
    help="在 hook 模式下，不覆盖已存在内容的提交信息文件",
)
@click.option("--provider", type=str, help="覆盖 LLM provider (例如 'openai')",)
@click.option("--model", type=str, help="覆盖 LLM 模型名称 (例如 'gpt-4o-mini')",)
@click.option("--template", type=str, help="覆盖要使用的模板文件",)
@click.pass_context
@click.option(
    "--from-hook",
    nargs=2,
    type=click.Path(),
    default=(None, None),
    help="由 git hook 调用。接收 [commit_msg_file, commit_source]。内部使用。",
    hidden=True,
)
def generate(ctx, config_path: str, dry_run: bool, no_overwrite: bool, provider: str, model:str, template: str, from_hook: tuple[str, str]):
    """
    生成提交信息。
    """
    console = Console()
    verbose = ctx.obj.get('verbose', False)
    commit_msg_file, commit_source = from_hook
    is_hook_run = commit_msg_file is not None

    try:
        # 0. 加载配置 (优先，因为 hook 逻辑可能需要配置)
        config = load_and_merge_configs(custom_config_path=config_path)

        # 如果从 hook 运行，执行 hook 的特定逻辑
        if is_hook_run:
            if not config.hook.enabled:
                return  # Hook is disabled in config

            # 如果用户提供了 -m, --template, 或者正在进行 merge/squash/amend，则跳过
            if commit_source in ("message", "template", "merge", "squash"):
                return

            # 检查文件是否已包含内容
            if os.path.exists(commit_msg_file) and os.path.getsize(commit_msg_file) > 0:
                # CLI flag takes precedence over config
                should_overwrite = not config.hook.no_overwrite
                if no_overwrite is not None: # a boolean value was passed
                    should_overwrite = not no_overwrite

                if not should_overwrite:
                    return

        # 1. 前置检查
        if not is_git_repository():
            raise AICommitException("不是一个 Git 仓库。请在 Git 仓库的根目录运行此命令。")
        if not has_staged_changes():
            raise AICommitException("没有发现暂存区的变更。请先执行 git add 命令。")

        # 2. 应用CLI覆盖
        config = apply_cli_overrides(config, provider, model, template)

        # 3. 运行流水线
        message = ""
        # 在 hook 模式下，不显示状态，以免污染 git 输出
        status_context = console.status("[bold green]正在生成提交信息...[/bold green]") if not is_hook_run else open(os.devnull, 'w')
        with status_context:
            try:
                message = asyncio.run(run_generation(config))
            except Exception as e:
                logger.error(f"生成提交信息时出错: {e}", exc_info=verbose)
                raise AICommitException(f"生成提交信息时出错: {e}")

        # 4. 处理输出
        if is_hook_run:
            with open(commit_msg_file, "w", encoding="utf-8") as f:
                f.write(message)
            # hook 模式下静默退出
            return

        console.print(Panel(
            message,
            title="[bold cyan]生成的提交信息[/bold cyan]",
            border_style="cyan",
            expand=False,
        ))

        if not dry_run:
            commit(message)
            console.print("\n[bold green]✅ 提交成功![/bold green]")
        else:
            console.print("\n[yellow]当前为预览模式。要提交信息，请移除 '--dry-run' 参数。[/yellow]")

    except AICommitException as e:
        logger.error(f"发生已知错误: {e}", exc_info=verbose)
        # 在 hook 模式下，不要打印到控制台，以免干扰 git
        if not is_hook_run:
            console.print(f"[bold red]错误:[/bold red] {e}")
    except Exception as e:
        logger.error(f"发生未知错误: {e}", exc_info=True)
        if not is_hook_run:
            console.print(f"[bold red]发生未知错误:[/bold red] {e}")


@cli.command("install-hook")
def install_hook():
    """
    安装 git hook 以在 'git commit' 时自动生成消息。
    """
    console = Console()
    if not is_git_repository():
        console.print("[bold red]错误:[/bold red] 不是一个 Git 仓库。")
        return

    hooks_dir = os.path.join(".git", "hooks")
    hook_path = os.path.join(hooks_dir, "prepare-commit-msg")

    if not os.path.exists(hooks_dir):
        os.makedirs(hooks_dir)

    if os.path.exists(hook_path):
        with open(hook_path, "r", encoding="utf-8") as f:
            content = f.read()
            if "Managed by aicommit" not in content:
                console.print(f"[bold yellow]警告:[/bold yellow] 一个自定义的 'prepare-commit-msg' hook 已存在。")
                if not click.confirm("你确定要覆盖它吗? (建议先备份)"):
                    return

    with open(hook_path, "w", encoding="utf-8") as f:
        f.write(HOOK_SCRIPT)

    # 赋予执行权限
    st = os.stat(hook_path)
    os.chmod(hook_path, st.st_mode | stat.S_IEXEC)

    console.print("[bold green]✅ Git hook 安装成功![/bold green]")
    console.print("现在，当你运行 'git commit' 时，将自动为你生成提交信息。")


@cli.command("uninstall-hook")
def uninstall_hook():
    """
    卸载 aicommit 的 git hook。
    """
    console = Console()
    if not is_git_repository():
        console.print("[bold red]错误:[/bold red] 不是一个 Git 仓库。")
        return

    hook_path = os.path.join(".git", "hooks", "prepare-commit-msg")

    if os.path.exists(hook_path):
        with open(hook_path, "r", encoding="utf-8") as f:
            content = f.read()

        if "Managed by aicommit" in content:
            os.remove(hook_path)
            console.print("[bold green]✅ Git hook 卸载成功![/bold green]")
        else:
            console.print("[bold yellow]警告:[/bold yellow] 'prepare-commit-msg' hook 不是由 aicommit 安装的。请手动移除。")
    else:
        console.print("[yellow]未找到 aicommit 的 git hook。[/yellow]")


if __name__ == "__main__":
    cli()
