import inspect
from typing import Any, Callable, Dict, Type, TypeVar

T = TypeVar("T")


class Registry:
    """A registry for storing and retrieving classes."""

    def __init__(self, name: str):
        """
        Initializes the registry.

        Args:
            name: The name of the registry (e.g., "collector", "provider").
        """
        self._name = name
        self._components: Dict[str, Type[Any]] = {}

    def register(self, name: str) -> Callable[[Type[T]], Type[T]]:
        """
        A decorator to register a class with a given name.

        Args:
            name: The name to register the class under.

        Returns:
            The decorator.

        Raises:
            ValueError: If the name is already registered.
        """
        def decorator(cls: Type[T]) -> Type[T]:
            if name in self._components:
                raise ValueError(f"Component '{name}' already registered in '{self._name}' registry.")
            self._components[name] = cls
            return cls
        return decorator

    def get(self, name: str) -> Type[Any]:
        """
        Retrieves a class by its name.

        Args:
            name: The name of the class to retrieve.

        Returns:
            The class type.

        Raises:
            KeyError: If the name is not registered.
        """
        if name not in self._components:
            raise KeyError(f"Component '{name}' not found in '{self._name}' registry.")
        return self._components[name]

    def create(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Instantiates a component by its name.

        Args:
            name: The name of the component to instantiate.
            *args: Positional arguments to pass to the constructor.
            **kwargs: Keyword arguments to pass to the constructor.

        Returns:
            An instance of the component.
        """
        component_class = self.get(name)
        return component_class(*args, **kwargs)

    def __contains__(self, name: str) -> bool:
        return name in self._components

    def __iter__(self):
        return iter(self._components)

    def keys(self):
        return self._components.keys()


collector_registry = Registry("collector")
provider_registry = Registry("provider")
