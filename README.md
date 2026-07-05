# GitSmart 🥇
A smart and autonomous developer companion platform designed to streamline code reviews and architecture analysis. By combining semantic knowledge graphs with multi-agent orchestration, the system provides automated, context-rich reviews directly on pull requests and powers an interactive codebase assistant.

## The Idea 💡
AI agents are great to write the code from the current context, create the pull request into the repo. No human intervention needed from the person writing the code. But what about the author reviewing 100's of pr every day, figuring out the diff, swtiching back and forth to find out if the pr is worth it or not. And if by any chance a PR is not reviewd properly and it introduces a bug immediately or later some other code is merged, the trace back and debugging becomes hell.
This is where Git Smart comes in. In an Open Source project where everyone wants to merge their PR and earn a badge, Git Smart makes it easier for the author to understand whether the created PR is actually worthy or not. It is a multi-agent platform and the memory is procided by Cognee.

Initial idea was to create a Git-compatible code hosting platform where ai agents and humans both work together to write, review and merge the code. But creating such a platform even for a demo would take weeks to show good results. Hence we stumbled upon a third-party platform that integrates with Github and ingests your repo to create a mindmap of your files.

<br/>

## How does it work?

## How is Cognee used?
Cognee is the **brain** of this platform.
- It ingests the repo, constructs the memory of the github repo, and stores all the relationships of the data, the architectural designs in it self.
- When the repo is changed, whether it is removing the code or writing new. The triggered webhook helps cognee to update its memory accordingly.
- The PR Reviewer: This is main functionality of the platform. It is not just a basic PR reviewing but an intelligent one that understand your code and immediately scans the PR, its diff, and then answers.
