from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import time
from datetime import datetime, timedelta
import argparse
import sys

def parse_args():
    parser = argparse.ArgumentParser(description='action.yml arguments')
    parser.add_argument('--username', type=str, help='Username (case-insensitive)')
    parser.add_argument('--password', type=str, help='Password (case-insensitive)')
    parser.add_argument('--building_name', type=str, help='Select a Building')
    parser.add_argument('--floor', type=str, help='Floor Acronym Number, ex. JT01')
    parser.add_argument('--workstation', type=str, help='WorkPoint-WorkStation')
    return parser.parse_args()

class archibus_scheduler():
    def __init__(self, args):
        # get user input passed by args
        self.username = args.username
        self.password = args.password
        self.building_name = args.building_name
        self.floor = args.floor
        self.workstation = args.workstation

        # derive args
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.next_month = str((datetime.now() + timedelta(weeks=4)).strftime("%Y-%m-%d"))
        self.next_month_day = str((datetime.now() + timedelta(weeks=4)).strftime("%#d"))

    ## Setup Webdriver
    def setup(self):

        service = Service(ChromeDriverManager().install())
        chrome_options = webdriver.ChromeOptions() 
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument("--disable-notifications")

        self.driver = webdriver.Chrome(service=service, options = chrome_options)
        
        # Min Page Load Time
        self.driver.implicitly_wait(5) 

    # Known Popups
    def popups(self):
        try:
            ## Recommended seat assignment
            reassignment = self.driver.find_element(By.CSS_SELECTOR, '[class*="DontShowButton"]') 
            reassignment.click()
        except NoSuchElementException:
            pass
        try:
            # Time slot of today's booking has passed
            reassignment = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Close')]")
            reassignment.click()
        except NoSuchElementException:
            pass

    # Selenium Actions to Walk Webpage
    def actions(self):

        # Setup
        self.setup()

        # Archibus Webpage
        self.driver.get("https://pathfinder.horizantsolutions.com/archibus/schema/ab-products/essential/workplace/index.html")

        ## Login Page
        input_username = self.driver.find_element(by=By.ID,value='logon-user-input')
        input_username.send_keys(self.username)

        input_password = self.driver.find_element(by=By.ID,value='logon-password-input')
        input_password.send_keys(self.password)

        input_log_in = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="logon-sign-in-btn"]') # 'logon-sign-in-btn'
        input_log_in.click()
        print(f"Logged In: {self.username}")

        ## Building Page
        # Find all elements where the class name contains "BuildingName"
        building_elements = self.driver.find_elements(By.CSS_SELECTOR, '[class*="BuildingName"]')

        # Iterate through the elements and find the one containing "Jean Talon"
        for element in building_elements:
            if self.building_name in element.text:
                input_building = element
                break

        input_building.click()
        print(f'Building Selected: {input_building.text}')

        ## Workspace 
        input_building = self.driver.find_element(By.CSS_SELECTOR, value='div.DashboardCard__CardContainer-sc-1eazl8g-0.igvAnp') # assume Workspace is first Card
        input_building.click()  

        ### Workspace Booking

        # Known stop for popups
        self.popups()

        ## StartDate
        calendar = self.driver.find_element(By.ID, 'startData_icon')
        calendar.click()

        input_next_month = self.driver.find_element(By.XPATH, "//button[@aria-label='Select next month']")
        input_next_month.click()

        # Look for a class with the day value of 1 month from today
        input_day = self.driver.find_element(By.XPATH, f"//div[contains(@class, 'react-datepicker__day') and contains(text(), '{self.next_month_day}')]")
        input_day.click()
        print(f'Date Selected: {self.next_month}')

        # Select Floor
        input_floor = self.driver.find_element(By.XPATH, f"//div[contains(text(), '{self.floor}')]")
        input_floor.click()
        print(f'Floor Selected: {self.next_month}')

        ## Select Seat
        input_selected_seat = self.driver.find_element(By.XPATH, f"//p[contains(text(), '{self.workstation} -')]")
        print(f"Found element: {input_selected_seat.text}")
        input_selected_seat.click()

        # Book Seat
        input_book_seat = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Book')]")
        input_book_seat.click()

        # Book for 'Myself'
        input_book_myself = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Myself')]")
        input_book_myself.click()

        # Confirm Booking
        input_book_seat = self.driver.find_element(By.XPATH, "//button[contains(text(), 'BOOK')]")
        input_book_seat.click()

        self.driver.close()


if __name__ == "__main__":

    # simulated args for testing
    # sys.argv = [ 'main.py',
    #              '--username', 'LASTFIRST',
    #              '--building_name', 'BUILDING',
    #              '--floor', 'ACRONYMNUMBER',    
    #              '--workstation', 'NUMBER',
    #              '--password', 'PASSWORD'
    #              ]

    args = parse_args()
    scheduler = archibus_scheduler(args)
    scheduler.actions()
