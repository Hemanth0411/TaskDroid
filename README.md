# TaskDroid: Autonomous AI Agent for Android Applications

<div align="center">
  <!-- Project logo: Replace the URL with your actual logo image before publishing -->
  <!--<img src="https://i.imgur.com/your-project-logo-url.png" alt="TaskDroid Logo" width="200"/> -->
  <p><strong>An intelligent agent for automating and exploring Android apps using Vision-Language Models.</strong></p>
  <p>
    <a href="#key-features">Features</a> |
    <a href="#getting-started">Getting Started</a> |
    <a href="#usage">Usage</a> |
    <a href="#architecture">Architecture</a> |
    <a href="#configuration">Configuration</a> |
    <a href="#contributing">Contributing</a>
  </p>
</div>

TaskDroid is an advanced AI-driven system designed to autonomously interact with Android applications. Utilizing Vision-Language Models (VLMs), it can understand UI screens, perform goal-oriented tasks, and explore app functionalities. Through its modular architecture and intelligent feedback loop, TaskDroid serves as a robust platform for mobile app automation and analysis.

---

## Key Features

* **Natural Language Task Decomposition**: Interprets high-level instructions into sequential sub-goals.
* **Autonomous Execution**: Interacts with UI elements via tapping, swiping, and text input without manual intervention.
* **Self-Exploration Mode**: Explores unknown apps, documents UI elements, and stores knowledge for future use.
* **Reflective Correction**: Implements a think-act-reflect loop to identify and recover from mistakes.
* **Multi-Modal Understanding**: Employs VLMs to visually comprehend UI structures.
* **Modular & Configurable**: Easily adaptable to various VLMs and device setups.
* **Grid-Based Backup Interaction**: Utilizes a fallback grid for direct screen interactions when UI parsing fails.

---

## Getting Started

### Prerequisites

* Python 3.9 or higher
* Android SDK Platform-Tools (`adb` in PATH)
* Android device/emulator with Developer Mode & USB Debugging
* AAPT (in Android SDK `build-tools` directory)

### Installation

```bash
git clone https://github.com/your-username/TaskDroid.git
cd TaskDroid
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Configuration

1. Copy the sample configuration:

```bash
cp settings.example.yaml settings.yaml
```

2. Update `settings.yaml` with your API keys:

```yaml
vlm_provider: "gemini"

gemini:
  api_key: "YOUR_GEMINI_API_KEY"
  model_name: "gemini-1.5-pro-latest"

openai:
  api_key: "YOUR_OPENAI_API_KEY"
  model_name: "gpt-4o"
```

Environment variables (`GEMINI_API_KEY`, `OPENAI_API_KEY`) will override these values if present.

---

## Usage

### Task Execution Mode

```bash
python -m task_droid.orchestrator path/to/calculator.apk "Calculate 12 plus 25 and show the result"
```

### Exploration Mode

```bash
python -m task_droid.orchestrator path/to/app.apk "Explore the main features of this app"
```

The agent will analyze, plan, and interact with the app accordingly, saving knowledge to `app_output/<AppName>/knowledge_base/`.

---

## Architecture

<p align="center">
  <img src="https://i.imgur.com/your-architecture-diagram.png" alt="Architecture Diagram"/>
</p>

1. **Initialization**: The orchestrator analyzes the APK, installs it, and sets up the device.
2. **Planning**: The navigator decomposes tasks using the VLM.
3. **Perceive-Think-Act Loop**:

   * *Perceive*: Screenshots and XML hierarchies are collected.
   * *Think*: The VLM processes the current state and determines the next action.
   * *Act*: Actions are executed on the device.
4. **Reflection**: Outcomes are compared and used to document and learn UI element behavior.
5. **Cleanup**: Finalization and resource cleanup after task completion.

---

## Configuration

Customize behavior in `settings.yaml`:

* `vlm_provider`: Select VLM ("gemini", "openai")
* `agent.max_task_rounds`: Maximum iterations for a task
* `agent.app_load_delay_sec`: Delay after launching an app
* `device.min_element_dist`: Adjust element detection sensitivity

---

## Contributing

We welcome contributions to TaskDroid!

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'Add feature'`
4. Push and open a pull request

Please follow the existing style and provide test coverage where applicable.

---

*Note: Replace placeholder image URLs with actual assets before publishing.*
