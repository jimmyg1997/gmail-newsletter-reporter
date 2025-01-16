# Gmail Newsletter Reporter 📬📊

Gmail Reporter is a Python-based automation project that integrates Gmail, Google Sheets, Google Docs, and OpenAI APIs to streamline email summarization and report generation. It leverages advanced APIs and CLI configurations to provide a seamless experience for managing and analyzing email communications.


---

## 📦 **Usage**
*Join My Telegram Channel to Receive Newsletter Summaries:*

1. Join my Telegram channel to receive summaries of newsletters from my Google email subscriptions. You can find the summary data in the linked [Google Sheets](link-to-your-google-sheets).
2. Press /help to check all the available commands
3. Press /register_ to register
4. Once you're registered, the summaries will be delivered automatically once per day ()


---

## ⚙️ **Set-up**
*Set Up the Script to Run on Your Own:*

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/jimmyg1997/gmail-newsletter-reporter
   cd gmail-newsletter-reporter
   ```

2. **Set Up Conda Virtual Environment:**

- First, Ensure that you have Conda installed on your system [here](https://docs.conda.io/projects/conda/en/latest/user-guide/install/). and reate a new Conda virtual environment:
   ```bash
   conda create --name venv-newsletter-reporter python=3.11
   ```
- Activate the Conda virtual environment:
   ```bash
   conda activate newsletter-reporter
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables:**
- Copy the `config/config.ini.example` file to `config/config.ini` and fill in the required values


   ```bash
   [api_telegram]
   token_key = 
   [api_openai]
   token_key = 
   ```

5. **Run the Script:**
   ```bash
   python main.py --hours 24 --schedule_hour 9 --enable_polling
   ```


---

## 🚀 **Features**

### 📧 Email Retrieval and Analysis
- **Dynamic Email Fetching:**
  - Uses the `GoogleEmailAPI` to retrieve emails based on a configurable time window (e.g., last 24 hours).
  - Parses subject, sender, and email body for analysis.
- **Content Summarization:**
  - Summarizes email content using OpenAI's GPT models.
  - Extracts token usage statistics for tracking API costs.
- **Categorization:**
  - Automatically classifies emails into newsletters or custom categories.

### 📝 Report Generation
- **Summary Reports:**
  - Generates detailed `.txt` summaries for each email.
  - Appends summarized content to a Google Doc titled `(Year Month) Newsletters Summaries`.
- **Google Sheets Integration:**
  - Saves configuration and execution metrics (e.g., number of emails processed, token usage).
  - Dynamically updates Sheets for tracking.

### 🤖 Telegram Notifications (Optional)
- Integrates with `TelegramAPI` to send notifications or report summaries.
- Configurable via CLI to enable/disable Telegram polling.

### 🕒 Configurable Scheduling
- **Custom Scheduling:**
  - Supports CLI arguments to set:
    - Time window for email retrieval (`--hours`, `--days_diff`).
    - Scheduled execution hour (`--schedule_hour`).
    - Telegram polling (`--enable_polling`).
- **Automation:**
  - Runs continuously in a loop, with the ability to break out after completion.

---

## 🛠️ **Technical Workflow**

1. **Initialization:**
   - Fetch configuration data from Google Sheets (e.g., target folder IDs, reporting parameters).

2. **Email Retrieval:**
   - Connect to Gmail API and retrieve emails within the specified time window.
   - Extract metadata and body content for processing.

3. **Content Analysis:**
   - Use OpenAI's GPT API to:
     - Summarize email content.
     - Generate token statistics for monitoring costs.

4. **Report Generation:**
   - Save summaries as `.txt` files locally.
   - Update Google Docs and Google Sheets with categorized content.

5. **Notification:**
   - (Optional) Send reports via Telegram for instant updates.

6. **Logging:**
   - Record execution metrics (e.g., emails processed, token usage, runtime errors).

---

## ⚙️ **Configuration Options**

### **CLI Arguments:**
| Argument              | Description                                                | Example           |
|-----------------------|------------------------------------------------------------|-------------------|
| `--hours`             | Sets the time window for email retrieval in hours.         | `--hours 24`      |
| `--days_diff`         | Sets the time window for email retrieval in days.          | `--days_diff 7`   |
| `--schedule_hour`     | Hour to schedule script execution (24-hour format).        | `--schedule_hour 9` |
| `--enable_polling`    | Enables Telegram polling for notifications.                | `--enable_polling` |

### **Environment Variables:**
- `OPENAI_API_KEY`: API key for OpenAI GPT integration.
- `TELEGRAM_BOT_TOKEN`: Token for Telegram bot.
- `GMAIL_CREDENTIALS_JSON`: Path to Gmail API credentials JSON file.

### **Google API Configuration:**
- Requires Google API setup for:
  - Gmail API.
  - Google Drive API.
  - Google Sheets API.

---




## 📊 **Execution Metrics**
You can find more information about the metrics used in linked [Google Sheets](link-to-your-google-sheets).

| Metric                 | Description                                      |
|------------------------|--------------------------------------------------|
| **Emails Processed**   | Number of emails analyzed during execution.      |
| **Token Usage**        | Total tokens consumed by OpenAI API.             |
| **Execution Time**     | Duration of script execution.                    |
| ...     | ...                    |



---
## 💡 **Extensibility & Future Enhancements**
 
- **Error Handling and Resilience:**
   - Implement retry logic for API calls.
   - Add graceful fallback for transient errors.
- **Modularization:**
   - Break large functions into smaller, reusable units.
   - Abstract repetitive tasks (e.g., logging, API connection handling).
- **Testing and CI/CD:**
   - Use `pytest` to create unit tests for individual components.
   - Integrate CI/CD pipelines for automated testing.
-**Scalability:**
   - Implement asynchronous processing for fetching and summarizing emails.
   - Batch large datasets for memory optimization.
   - Add support for additional email providers (e.g., Outlook, Yahoo).
- **Advanced Analytics:**
   - Add Natural Language Processing (NLP) features for sentiment analysis.
   - Generate visualizations (e.g., trends in email volume).
- **Dashboarding**
   - Implement a web dashboard for real-time tracking of reports.

---


## 🛡️ **License**
This project is licensed under the MIT License. See the `LICENSE` file for details.

---

## 🤝 **Contributing**
Contributions are welcome! Feel free to open an issue or submit a pull request to enhance the functionality.
