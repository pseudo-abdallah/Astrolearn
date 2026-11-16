# Contributing

Choose a work package in docs/work-packages.md and work on a branch such as feature/ui-preview or feature/local-solver. Use pull requests to integrate changes.

Keep changes within the component you own where possible. Agree on changes to shared contracts before modifying both ends of an integration. Document setup, dependencies, configuration, and hardware assumptions with each executable component.

Explain newly written code with comments where useful, following the project's preference for annotated code. Never commit credentials, raw observation sessions, downloaded solver indexes, or model weights.

Test against simulated devices first. Document which checks ran and which require physical hardware. Do not claim placeholder components are implemented.
