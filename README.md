# 📬 Mail-Rememberer

Mail-Rememberer is a Python-based application designed to help users manage their daily tasks through automated email reminders. 📧 It sends a daily email with a list of tasks, and users can respond with their progress and future plans. The application then processes these responses, updates the task list, and incorporates this information into subsequent emails.

## ✨ Features

- **Daily Email Reminders**: Automatically sends an email every day with tasks that need to be completed.
- **Task Management**: Users can respond to the email with updates on their progress and future plans.
- **Data Storage**: Stores task information in a database for future reference and updates.
- **AI Integration**: Uses Mistral AI models to intelligently process and manage tasks.

## 🛠 Tech Stack

- **Python**: The core programming language used for the application.
- **GitHub Actions**: Automates the daily execution of the script.
- **Mistral AI Models**: Processes and manages tasks intelligently.
- **Postmark**: Handles the sending of emails.
- **SQLite3**: Stores task and message data locally.

## 🚀 Setup

### Prerequisites

- **git**: If you for some reason need to install it, [here](https://github.com/git-guides/install-git) are your instructions.
- **uv**: A python package and project manager that also handles downloading Python for you. Installation instructions can be found [here](https://docs.astral.sh/uv/getting-started/installation/). If you for some reason want to use another package manager, you will have to adapt the instructions accordingly.
- **Mistral AI API key**: A guide on how to obtain one can be found [here](https://docs.mistral.ai/getting-started/quickstart/#account-setup).
- **Postmark API key**: You can get started with using Postmark [here](https://postmarkapp.com/support/article/1002-getting-started-with-postmark).

### Local installation

1. Clone the repository:
   ```bash
   git clone https://github.com/HomerusJa/mail-rememberer.git
   cd mail-rememberer
   ```

2. Install the required packages using `uv`:
   ```bash
   uv sync
   ```

3. Rename the `.env.example` file to `.env`:
   ```bash
   mv .env.example .env
   ```

4. Fill the `.env` file. The keys you'll need to definitely change are `POSTMARK_SERVER_API_TOKEN`, `RECEIVER_MAIL` and `MISTRAL_API_KEY`. Guides on how to obtain these values can be found in the [prerequisites](#prerequisites).

5. That's it 🚀 Now, start a test run locally! Make sure you set the environment variable `ENV=dev`:
   ```bash
   uv run main.py
   ```

### Using with GitHub Actions

This project is designed to be used with GitHub Actions. For that, the [`remember.yml`](https://github.com/HomerusJa/mail-rememberer/blob/main/.github/workflows/remember.yml) workflow is provided. To use it, you will need to add your secrets to the repository.

1. Go to your fork on GitHub and click on the `Settings` tab.
2. In the sidebar, under `Code and automation`, click `Environments`.
3. Click `New environment`.
4. Call the environment `remember-env`
5. Set the following secrets as in your local `.env` file:
   - `POSTMARK_SERVER_API_TOKEN`
   - `MISTRAL_API_KEY`
6. Set the following variables as in your local `.env` file:
   - `RECEIVER_MAIL`
7. That's it! Now, you can start a test run on GitHub Actions!

> [!NOTE]
> Why didn't I just save everything as a secret? Because when something is saved as a secret, I can't see its contents (Which is great for API keys, but not for things like the receiver email address)

## 🎬 Usage

- **Development Mode**: When running in development mode, the script will drop existing tables and generate sample data for testing. This can be activated by setting the `ENV` environment variable to `dev`.
- **Production Mode**: In production mode, the script will use the existing database and send real emails to the specified receiver. This is not implemented yet.

## 🤝 Contributing

Contributions are welcome! Please fork the repository and create a pull request with your changes. Notes on how to set everything up can be found in the [setup](#setup) section.

## 📄 License

This project is licensed under the MIT License.
