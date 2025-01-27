import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from dotenv import load_dotenv
import csv
import time

# Load environment variables from .env file
load_dotenv()

# Credentials and URLs
username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")
login_url = os.getenv("LOGIN_URL")
directory_url = os.getenv("DIRECTORY_URL")

# Configure Chrome options
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--remote-debugging-port=9222")

# Specify the ChromeDriver path
service = Service("/path/to/chromedriver")  # Update this path as needed

# Start WebDriver
driver = webdriver.Chrome(service=service, options=options)

output_path = "./data/example_output.csv"

try:
    print("Opened login page.")
    driver.get(login_url)

    # Login
    username_field = driver.find_element(By.ID, "UserName")
    password_field = driver.find_element(By.ID, "Password")
    username_field.send_keys(username)
    password_field.send_keys(password)
    password_field.send_keys(Keys.RETURN)
    print("Logged in successfully!")
    time.sleep(3)

    driver.get(directory_url)
    print("Navigated to the directory page.")
    time.sleep(5)

    business_data = []
    page_number = 1

    while True:
        print(f"Scraping page {page_number}...")
        members = driver.find_elements(By.CSS_SELECTOR, ".mn-member-listing")
        print(f"Found {len(members)} members on this page.")

        if len(members) == 0:
            break

        for member in members:
            try:
                business_name_element = member.find_element(By.CSS_SELECTOR, ".mn-searchlisting-title a")
                business_name = business_name_element.text.strip()
                business_url = business_name_element.get_attribute("href")
                print(f"Processing: {business_name}")

                driver.execute_script("window.open(arguments[0]);", business_url)
                driver.switch_to.window(driver.window_handles[1])
                time.sleep(3)

                try:
                    email_element = driver.find_element(By.XPATH, "//a[contains(@href, 'mailto:')]")
                    email = email_element.text.strip()
                except:
                    email = "N/A"

                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(1)

                try:
                    phone_element = member.find_element(By.CSS_SELECTOR, ".mn-searchlisting-phone")
                    phone_number = phone_element.text.strip()
                except:
                    phone_number = "N/A"

                business_data.append({
                    "Business Name": business_name,
                    "Phone Number": phone_number,
                    "Email": email,
                })
            except:
                continue

        try:
            next_button = driver.find_element(By.CSS_SELECTOR, "li.next.nomargin a")
            next_button.click()
            page_number += 1
            time.sleep(5)
        except:
            print("No more pages.")
            break

    with open(output_path, "w", newline="") as csvfile:
        fieldnames = ["Business Name", "Phone Number", "Email"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(business_data)

    print(f"Data saved to '{output_path}'.")
finally:
    driver.quit()
    print("Browser closed.")
