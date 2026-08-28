SKILLS





***building a backend app from scratch***



This Backend Development \& Deployment Workflow will teach you how to develop a backend from scratch locally, and then deploy it publicly to fly.io using tools that are builtin to your system.

Use this workflow when the user asks you to build a backend app from scratch -- e.g. if they say "create an A

PI that does X".





\# Database





1\. For simple proof-of-concept apps, you can use an in-memory database. However, if the user needs data persistence,you can use SQLite with a persistent volume.

2\. To use persistent SQLite storage, deploy with the volume option: `<deploy\\\_backend dir="{{path to backend app}}" volume="True"/>`. This mounts a 1GB persistent volume at /data.

3\. When using persistent storage, configure your SQLite database path to /data/app.db. This data will persist across deployments and restarts.





\# Backend

1\. If the user did not specify a backend stack or asked for Python you must use `<shell id="setup" exec\\\_dir="\\\~"> create\\\_fastapi\\\_app {{app name}} </shell>` to create the app. This will setup a FastAPI app with Postgres already setup.

\- The scaffolding will include an app/main.py file. You MUST keep the CORS code untouched so that the backend works later when you deploy it. You MUST NOT remove or rename this file and you MUST keep the FastAPI instance named "app" inside this file since our deployment server expects it to be there.

2\. Now implement the backend. If using FastAPI, you need to add any additional dependencies using `poetry add <package name>`. It's important that the pyproject.toml file contains all needed dependencies since otherwise the deployment will fail.

\- If environment variables are needed, you should use a .env file in the backend directory and load them from there.

3\. If you need a database:

&#x20;  - For proof-of-concept without persistence: use an in-memory database

&#x20;  - For persistent data: use SQLite with the volume option (see Database section above)

4\. Test your backend endpoints using curl and iterate until they work as expected. For FastAPI, you can start the development server using `poetry run fastapi dev app/main.py`. This will auto-reload as you make changes.





\# Deployment

1\. Once the backend works, and if it uses FastAPI, deploy the backend:

&#x20;  - Without persistent storage: `<deploy\\\_backend dir="{{path to backend app}}"/>`

&#x20;  - With persistent SQLite storage: `<deploy\\\_backend dir="{{path to backend app}}" volume="True"/>`

&#x20;  You will receive a URL to access your backend.

\- If the user explicitly asked for a different backend stack, you should stop here and ask them for their preferred deployment method and necessary credentials (if they are not already present in your secrets).

4\. Share the backend URL with the user and let them know that you tested locally but still need to test the deployed version.





\# Production Testing

1\. Test the deployed backend thoroughly to make sure it works as expected.

\- Make improvements if you find any issues. Make sure the user is happy but don't do unnecessary work.

\- You can view the logs of the deployed backend app using the `<deploy\\\_backend logs="True"/>` command.

\- If you make updates to backend, you must redeploy the backend using the same <deploy\_backend> command again and let the user know.

2\. Notify the user every time you redeployed the backend, share the URL, and tell them what changes you made.

3\. If the user gives you feedback or further requests, you should go back to the "Backend" section (if the changes require a backend) and iterate from there.





IMPORTANT NOTES:

\- Do NOT create a git repo as that will not be needed.

\- Do not use this note when working in an existing repo.

\- If the user is asking you to work on an existing project/repo, and did not indicate that they want a publicly deployed backend, you should NOT use this workflow. This backend deployment workflow is only for standalone projects!





***deploying a frontend app that was built from scratch***



This Frontend Deployment Workflow will teach you how to deploy a local web app to the cloud in order to make it accessible to the user.





\- When deploying frontends that rely on a backend, ensure that the corresponding backend URL is public and properly configured in the frontend code. This can never be a localhost URL since those are not accessible to the deployed app.

\- You must build the app locally every time you deploy it. For example when using Vite, you must run `npm run build` before deploying.

\- Use the <deploy\_frontend dir="build\_dir"/> command to deploy a frontend-only app. For example when using Vite, the build\_dir is `dist`. This command is your only way to interact with the deployment.

\- Do NOT create a git repo as that will not be needed. Do NOT expect the deployment server to do any build process for you; you must do that locally.

\- The build\_dir directory must contain all the files needed to deploy since not other content will be deployed.

\- Do not use this note when working in an existing repo.





***When asked to build a webscraper / web spider / web crawler to extract data from site(s)***



You can only develop headless webscrapers. Headful webscrapers will conflict with your machine's builtin browser.

Stick to Selenium and ChromeDriver for webscraping.





IF the user asks you:

\- To build a non-headless webscraper

\- To build a webscraper that requires doing impossible things in a headless browser (ex. solving CAPTCHAs)





Kindly let the user know that these features are not possible and suggest alternative less-capable scrapers that might be useful.





\## Purpose

Centralized governance and quality assurance framework for managing a portfolio of premium applications. Enforces a "Zero Tolerance" policy for bugs and strict completion criteria before production deployment.





\## Key Technologies

Markdown, Git, Cursor AI (MDC rules), Expo, React Native, Vercel, Netlify, better-auth, Jest.





\## Top-Level Structure

\*   `.cursor/rules/`: Programmatic AI instructions for development standards.

\*   `APP\\\_COMPLETION\\\_TRACKER.md`: Master status registry and deployment gatekeeper.

\*   `QUALITY\\\_CONTROL.md`: 100-point scoring framework and audit criteria.

\*   `TESTING\\\_VERIFICATION.md`: Mandatory QA protocols and sign-off checklists.

\*   `DOPAMINE\\\_UX\\\_GUIDE.md`: Behavioral design and interaction specifications.

\*   `APP\\\_INVENTORY.md`: Registry of assets migrated from iCloudDrive.

\*   `COMPLETE\\\_APP\\\_LIST.md`: Sequence for autonomous application finalization.

\*   `USER\\\_DOC.md`: Core standards for app management and structure.

\*   `CAROUSEL\\\_APP\\\_ANALYSIS.md`: Technical breakdown of multi-brand social media tools.





\## Key Concepts

\*   \*\*90+ Quality Score\*\*: Minimum threshold required for production readiness.

\*   \*\*Zero Tolerance Policy\*\*: Absolute prohibition of bugs or user dissatisfaction.

\*   \*\*Dopamine-driven UX\*\*: Design focused on instant gratification and engagement.

\*   \*\*One-Time Completion Rule\*\*: Mandate to perfect one version rather than iterate.

\*   \*\*Brains and Engines\*\*: External high-level logic sources for feature enhancement.

\*   \*\*Export Fix\*\*: Specific resolution for audio/video rendering issues.

\*   \*\*Flow State\*\*: UX goal of frictionless, balanced user interaction.

\*   \*\*Quick Wins\*\*: Rapid user success milestones in onboarding.

\*   \*\*Autonomous Completion\*\*: Process of systematic app elevation and migration.

\*   \*\*Pixel-perfect\*\*: UI implementation matching design with 100% accuracy.

\*   \*\*Cost-friendly API\*\*: Prioritization of efficient, low-overhead backend calls.

\*   \*\*Success Moment\*\*: Visual/auditory feedback sequence upon task completion.

\*   \*\*Executive Quality Control\*\*: Final human-in-the-loop verification phase.

\*   \*\*Unlock Mechanics\*\*: Progressive disclosure of features to manage load.

\*   \*\*Chaos Potential\*\*: Risk of system instability; grounds for immediate failure.





\## Purpose

A centralized governance and quality assurance framework for managing a multi-application ecosystem. It enforces strict "Production-Ready" standards and a mandatory 90/100 quality score for all software assets.





\## Key Technologies

Markdown, Cursor AI (.mdc rules), Expo, React Native, TypeScript, Jest, Vercel, Netlify.





\## Top-Level Structure

\*   `.cursor/rules/`: AI-assisted development standards and quality gates.

\*   `APP\\\_INVENTORY.md`: Central registry and deduplication log for cloud-sourced assets.

\*   `APP\\\_COMPLETION\\\_TRACKER.md`: Lifecycle status ledger for project readiness.

\*   `QUALITY\\\_CONTROL.md`: Quantitative scoring metrics and assessment criteria.

\*   `TESTING\\\_VERIFICATION.md`: Mandatory sign-off protocols and zero-bug policy.

\*   `DOPAMINE\\\_UX\\\_GUIDE.md`: Design specifications for high-engagement interfaces.

\*   `COMPLETE\\\_APP\\\_LIST.md`: Categorized directory of independent application modules.

\*   `.gitignore`: Restrictive whitelist-only version control configuration.





\## Key Concepts

\*   \*\*90+ Quality Score\*\*: Mandatory minimum threshold for production readiness.

\*   \*\*Zero Tolerance Policy\*\*: Strict rejection of any bugs or user dissatisfaction.

\*   \*\*Dopamine-Driven UX\*\*: Design focused on delight and high-engagement triggers.

\*   \*\*One-Time Completion Rule\*\*: Prohibition of redundant iterative recreations.

\*   \*\*Production-Ready\*\*: Status requiring 100% testing, verification, and documentation.

\*   \*\*Brains and Engines\*\*: External logic sources for advanced feature integration.

\*   \*\*Duplicate Management\*\*: Audit process to retain only the best version of an app.

\*   \*\*100% Proven\*\*: Requirement for successful execution in production environments.

\*   \*\*Pixel-Perfect\*\*: Visual standard for flawless, high-fidelity UI execution.

\*   \*\*Cost-Friendly API\*\*: Requirement for optimized, error-handled backend calls.

\*   \*\*Flow State\*\*: Design goal for frictionless, continuous user engagement.

\*   \*\*Confusion Points\*\*: UI/UX friction identified as blocking completion.

\*   \*\*Skeleton Screens\*\*: Structural placeholders used during content loading.

\*   \*\*Executive Sign-Off\*\*: Four-stage terminal approval process for releases.

\*   \*\*SSR Resolved\*\*: Specific fix status for Server-Side Rendering conflicts.





\## Purpose

Provides a standardized environment for repository data integrity. It ensures consistent file attribute handling and line-ending normalization across multiple operating systems.





\## Key Technologies

Git, Version Control System (VCS), Shell.





\## Top-Level Structure

\* `.gitattributes`: Configures line-ending normalization and file type detection.





\## Key Concepts

\* \*\*LF Normalization\*\*: Conversion of CRLF to LF during check-in.

\* \*\*Text Attribute\*\*: Flag identifying files for EOL processing.

\* \*\*Auto-detection\*\*: Heuristic analysis to distinguish text from binary data.

\* \*\*Line Endings\*\*: OS-specific characters (\\n vs \\r\\n) for terminating lines.

\* \*\*Pattern Matching\*\*: Wildcard-based application of attributes to file paths.



name: chrome-devtools description: Uses Chrome DevTools via MCP for efficient debugging, troubleshooting and browser automation. Use when debugging web pages, automating browser interactions, analyzing performance, or inspecting network requests. This skill does not apply to --slim mode (MCP configuration).

Core Concepts

Browser lifecycle: Browser starts automatically on first tool call using a persistent Chrome profile. Configure via CLI args in the MCP server configuration: npx chrome-devtools-mcp@latest --help.



Page selection: Tools operate on the currently selected page. Use list\_pages to see available pages, then select\_page to switch context.



Element interaction: Use take\_snapshot to get page structure with element uids. Each element has a unique uid for interaction. If an element isn't found, take a fresh snapshot - the element may have been removed or the page changed.



Workflow Patterns

Before interacting with a page

Navigate: navigate\_page or new\_page

Wait: wait\_for to ensure content is loaded if you know what you look for.

Snapshot: take\_snapshot to understand page structure

Interact: Use element uids from snapshot for click, fill, etc.

Efficient data retrieval

Use filePath parameter for large outputs (screenshots, snapshots, traces)

Use pagination (pageIdx, pageSize) and filtering (types) to minimize data

Set includeSnapshot: false on input actions unless you need updated page state

Tool selection

Automation/interaction: take\_snapshot (text-based, faster, better for automation)

Visual inspection: take\_screenshot (when user needs to see visual state)

Additional details: evaluate\_script for data not in accessibility tree

Parallel execution

You can send multiple tool calls in parallel, but maintain correct order: navigate → wait → snapshot → interact.



Troubleshooting

If chrome-devtools-mcp is insufficient, guide users to use Chrome DevTools UI:



https://developer.chrome.com/docs/devtools

https://developer.chrome.com/docs/devtools/ai-assistance

If there are errors launching chrome-devtools-mcp or Chrome, refer to https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/troubleshooting.md.

