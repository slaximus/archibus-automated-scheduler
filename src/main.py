from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
from datetime import datetime, timedelta
import argparse
import sys
import ast

def parse_args():
    parser = argparse.ArgumentParser(description='action.yml arguments')
    parser.add_argument('--username', type=str, help='Username (case-insensitive)')
    parser.add_argument('--password', type=str, help='Password (case-insensitive)')
    parser.add_argument('--building_name', type=str, help='Select a Building')
    parser.add_argument('--floor', type=str, help='Floor Acronym Number, ex. JT01')
    parser.add_argument('--workstation', type=str, help='WorkPoint-WorkStation')
    parser.add_argument('--workstation_backup', type=str, default='[]', required=False, help='WorkPoint-WorkStation-Backup')
    parser.add_argument('--advance_reservation', action='store_true', required=False, help='Book 4 weeks and one day ahead')
    return parser.parse_args()

class archibus_scheduler():
    def __init__(self, args):
        self.username = args.username
        self.password = args.password
        self.building_name = args.building_name.replace("-", " ")
        self.floor = args.floor
        self.workstation = args.workstation
        self.workstation_backup = ast.literal_eval(args.workstation_backup)
        self.advance_reservation = args.advance_reservation

        # Dates
        if self.advance_reservation:
            booking_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(weeks=4, days=1)
        else:
            booking_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(weeks=4)

        self.next_month = booking_date.strftime("%Y-%m-%d")
        self.next_month_day = str(booking_date.day)

        # Seat formatted datetime for UI
        self.seat_date = booking_date.strftime("Choose %A, %B %d, %Y")
        suffix = "th" if 11 <= int(self.next_month_day) <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(int(self.next_month_day) % 10, "th")
        self.seat_date = self.seat_date.replace(f"{int(self.next_month_day):02d}", f"{int(self.next_month_day)}{suffix}", 1)

        if self.workstation == '101' and self.floor == 'JT07' and self.username != 'EVANJUS':
            raise Exception('Workstation is unavailable.')

    def setup(self):
        service = Service(ChromeDriverManager().install())
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument("--disable-notifications")

        SELENIUM_GRID_URL = 'http://localhost:4444/wd/hub'
        self.driver = webdriver.Remote(command_executor=SELENIUM_GRID_URL, options=chrome_options, keep_alive=True)
        self.driver.implicitly_wait(15)
        self.wait = WebDriverWait(self.driver, 10)

    def popups(self):
        try:
            self.driver.find_element(By.CSS_SELECTOR, '[class*="DontShowButton"]').click()
        except NoSuchElementException:
            pass
        try:
            self.driver.find_element(By.XPATH, "//button[contains(text(), 'Close')]").click()
        except NoSuchElementException:
            pass
        try:
            self.driver.find_element(By.XPATH, "//button[contains(text(), 'Yes')]").click()
        except NoSuchElementException:
            pass

    def seat_selection(self):
        seat_options = [self.workstation]
        seat_options.extend(self.workstation_backup)
        seat_found = False
        for seat in seat_options:
            if seat_found:
                break
            workstation_formats = [
                f"//p[contains(text(), '{seat} - Primary')]",
                f"//p[contains(text(), '{self.floor}-{int(seat):02} - Secondary')]"
            ]
            for format in workstation_formats:
                try:
                    input_selected_seat = self.driver.find_element(By.XPATH, format)
                    print(f"Seat Selected: {input_selected_seat.text}")
                    input_selected_seat.click()
                    seat_found = True
                    break
                except:
                    print(f"Seat Unavailable: {seat}")
        if not seat_found:
            raise NoSuchElementException("No available seat found")

    def actions(self):
        self.setup()
        self.driver.get("https://pathfinder.horizantsolutions.com/archibus/login.axvw")

        # ✅ Corrected Login
        input_username = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.ID, 'username_input'))
        )
        input_username.send_keys(self.username)

        input_password = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.ID, 'password_input'))
        )
        input_password.send_keys(self.password)

        input_log_in = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'signin_button'))
        )
        input_log_in.click()
        print("User Logged In")

        # Create Workspace Booking
        try:
            input_workspace_booking = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, "//div[contains(text(), 'CREATE WORKSPACE BOOKING')]"))
            )
            input_workspace_booking.click()
        except NoSuchElementException:
            print("Already on booking page")

        # Select Building
        input_building = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, f"//div[contains(text(), '{self.building_name}')]"))
        )
        input_building.click()

        # Calendar
        self.popups()
        calendar = self.driver.find_element(By.ID, 'startData_icon')
        calendar.click()
        input_next_month = self.driver.find_element(By.XPATH, "//button[@aria-label='Select next month']")
        input_next_month.click()

        date = self.driver.find_element(By.XPATH, f"//div[@aria-label='{self.seat_date}']")
        ActionChains(self.driver).move_to_element(date).click().perform()

        time.sleep(2)
        input_floor = self.driver.find_element(By.XPATH, f"//div[text() = '{self.floor}']")
        input_floor.click()
        time.sleep(2)
        self.driver.find_element(By.XPATH, "//button[text() = 'Search']").click()
        time.sleep(2)

        self.seat_selection()
        time.sleep(2)

        self.driver.find_element(By.XPATH, "//button[text() = 'Book']").click()
        time.sleep(2)
        self.driver.find_element(By.XPATH, "//span[text() = 'Myself']").click()
        time.sleep(2)
        self.driver.find_element(By.XPATH, "//button[text() = 'BOOK']").click()
        time.sleep(2)

        self.popups()
        self.driver.find_element(By.XPATH, "//button[contains(text(),'GO TO MAIN')]").click()
        print("Booking confirmed")

        self.driver.quit()

if __name__ == "__main__":
    args = parse_args()
    scheduler = archibus_scheduler(args)
    scheduler.actions()
