import os
import openai
import csv
import time
from dotenv import load_dotenv  # Load environment variables
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Load environment variables from .env file
load_dotenv()

# Securely retrieve API key and login credentials
openai_api_key = os.getenv("OPENAI_API_KEY")
username = os.getenv("CHAMBER_USERNAME")
password = os.getenv("CHAMBER_PASSWORD")

if not openai_api_key or not username or not password:
    raise ValueError("Missing API key or credentials in .env file!")

# Initialize OpenAI client
client = openai.Client(api_key=openai_api_key)

# Configure Chrome options
options = webdriver.ChromeOptions()
options.binary_location = "/snap/bin/chromium"
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--remote-debugging-port=9222")

# Specify the ChromeDriver path
service = Service("/usr/local/bin/chromedriver")

# Start WebDriver
driver = webdriver.Chrome(service=service, options=options)

# CSV output file
output_path = "worcester_directory_filtered.csv"

# Function to categorize industry using OpenAI
def categorize_industry(description):
    if not description or description == "N/A":
        return "Unknown"

    prompt = f"Based on the following business description, determine the industry category in a single word:\n\n'{description}'\n\nExample responses: Healthcare, Finance, Technology, Retail, Real Estate, Education, Manufacturing, Consulting, Legal, Hospitality, Entertainment, Logistics, Construction, Energy, Food, Government, Nonprofit, Sports, Travel."

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Error categorizing industry: {e}")
        return "Unknown"

try:
    print("Current working directory:", os.getcwd())

    # Step 1: Open the login page
    login_url = "https://worcesterchamber.chambermaster.com/Login/"
    driver.get(login_url)
    print("Opened login page.")

    # Step 2: Locate username and password fields
    username_field = driver.find_element(By.ID, "UserName")
    password_field = driver.find_element(By.ID, "Password")

    # Step 3: Enter credentials and log in
    username_field.send_keys(username)
    password_field.send_keys(password)
    password_field.send_keys(Keys.RETURN)
    print("Logged in successfully!")
    time.sleep(3)

    # Step 4: Navigate to the directory page
    directory_url = "https://worcesterchamber.chambermaster.com/mic/members/search?lm=250&d=Ascending&memId=35962&repId=53751"
    driver.get(directory_url)
    print("Navigated to the directory page.")
    time.sleep(5)

    # Extract members from the directory
    business_data = []
    page_number = 1

    while True:
        print(f"Scraping page {page_number}...")

        members = driver.find_elements(By.CSS_SELECTOR, ".mn-member-listing")
        print(f"Found {len(members)} members on this page.")

        if len(members) == 0:
            print("No members found on this page. Stopping.")
            break

        for member in members:
            try:
                # Extract business name and details page link
                business_name_element = member.find_element(By.CSS_SELECTOR, ".mn-searchlisting-title a")
                business_name = business_name_element.text.strip()
                business_url = business_name_element.get_attribute("href")
                print(f"Processing: {business_name}")

                # Navigate to the business page
                driver.execute_script("window.open(arguments[0]);", business_url)
                driver.switch_to.window(driver.window_handles[1])
                time.sleep(3)

                # Extract "About" section
                try:
                    about_section = driver.find_element(By.ID, "about")
                    paragraphs = about_section.find_elements(By.TAG_NAME, "p")
                    about_text = "\n".join([p.text.strip() for p in paragraphs if p.text.strip()])
                except Exception as e:
                    print(f"'About' section not found for {business_name}: {e}")
                    about_text = "N/A"

                # Use OpenAI to categorize industry
                industry_category = categorize_industry(about_text)

                # Extract email
                try:
                    email_element = driver.find_element(By.XPATH, "//a[contains(@href, 'mailto:')]")
                    email = email_element.text.strip()
                except Exception as e:
                    print(f"Email not found for {business_name}: {e}")
                    email = "N/A"

                # Close the business detail page and switch back to the directory
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(1)

                # Extract the second representative (index 1)
                try:
                    representative_links = member.find_elements(By.CSS_SELECTOR, "div div a.mn-list-item-link")
                    representative = representative_links[1].text.strip() if len(representative_links) > 1 else "N/A"
                except Exception as e:
                    print(f"Representative not found: {e}")
                    representative = "N/A"

                # Extract phone number
                try:
                    phone_element = member.find_element(By.CSS_SELECTOR, ".mn-searchlisting-phone")
                    phone_number = phone_element.text.strip()
                except Exception as e:
                    print(f"Phone number not found: {e}")
                    phone_number = "N/A"

                # Add data to list
                business_data.append({
                    "Business Name": business_name,
                    "Phone Number": phone_number,
                    "Representatives": representative,
                    "Email": email,
                    "About": about_text,
                    "Industry": industry_category,
                })

            except Exception as e:
                print(f"Error processing member: {e}")

        # Navigate to the next page
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, "li.next.nomargin a")
            next_button.click()
            page_number += 1
            time.sleep(5)
        except Exception as e:
            print(f"No more pages to navigate or error occurred: {e}")
            break

    # Step 5: Save data to a CSV file
    try:
        with open(output_path, "w", newline="") as csvfile:
            fieldnames = ["Business Name", "Phone Number", "Representatives", "Email", "About", "Industry"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(business_data)

        print(f"Data saved to '{output_path}'.")
    except Exception as e:
        print(f"Error saving CSV: {e}")

finally:
    driver.quit()
    print("Browser closed.")
