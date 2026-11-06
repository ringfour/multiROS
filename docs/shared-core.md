# Shared core and robot ownership

The current ownership model and integration status are in
[Architecture](architecture.md). Follow [Adding a robot](porting.md) to integrate
a recipe, and [Validation](../VALIDATION.md) for tested setups and limits.

## Pixi is the host interface

Robots expose shared host actions through their own Pixi tasks. See
[Commands](commands.md) and [Configuration](configuration.md) for that contract.
