from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
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
        self.building_name = args.building_name.replace("-", " ")
        self.floor = args.floor
        self.workstation = args.workstation

        # Dates
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.next_month = str((datetime.now() + timedelta(weeks=4)).strftime("%Y-%m-%d"))
        self.next_month_day = str((datetime.now() + timedelta(weeks=4)).strftime("%#d")).lstrip("0")

        # Seat formatted datetime
        self.seat_date = (datetime.now() + timedelta(weeks=4)).strftime("Choose %A, %B %d, %Y")
        day = (datetime.now() + timedelta(weeks=4)).day
        suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        self.seat_date = self.seat_date.replace(f"{day:02d}", f"{day}{suffix}",1)

        # validate archnemesis
        if self.workstation == '28' and self.floor == 'JT01' and self.username != 'EVANJUS':
            raise Exception('Workstation is unavailable.')

    ## Setup Webdriver
    def setup(self):

        service = Service(ChromeDriverManager().install())
        chrome_options = webdriver.ChromeOptions() 
        chrome_options.add_argument("--window-size=1200,1200")
        chrome_options.add_argument("--headless")  # Headless mode
        chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
        chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
        chrome_options.add_argument("--disable-gpu")  # Disable GPU rendering
        chrome_options.add_argument("--remote-debugging-port=9222")  # Required for headless mode
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument("--disable-notifications")

        #self.driver = webdriver.Chrome(service=service, options = chrome_options)
        # Establish connection to the Dockerized Selenium Grid
        # Define the Selenium Grid URL (localhost:4444 in your case)
        SELENIUM_GRID_URL = 'http://selenium:4444/wd/hub'
        self.driver = webdriver.Remote(
            command_executor=SELENIUM_GRID_URL,
            options=chrome_options,
            keep_alive=True
        )
        
        # Min Page Load Time
        self.driver.implicitly_wait(15) 

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
        try:
            # A seat has already been booked, do you want to rebook
            reassignment = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Yes')]")
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
        print(f"User Logged In")

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
        # Manual time delays added as selenium able to find/click elements but fails on final booking button
        # WebDriverWait, ActionChains considered but did not resolve the issue

        # Known stop for popups
        self.popups()

        ## StartDate
        calendar = self.driver.find_element(By.ID, 'startData_icon')
        calendar.click()

        input_next_month = self.driver.find_element(By.XPATH, "//button[@aria-label = 'Select next month']")
        input_next_month.click()

        # Look for a class with the day value of 1 month from today
        # ActionChains used to simulate click of date, more specific aria-label used 
        date = self.driver.find_element(By.XPATH, f"//div[@aria-label='{self.seat_date}']")
        actions = ActionChains(self.driver)
        actions.move_to_element(date).click().perform()
        print(f'Date Selected: {self.next_month}')
        time.sleep(2)

        # Select Floor
        input_floor = self.driver.find_element(By.XPATH, f"//div[text() = '{self.floor}']")
        input_floor.click()
        print(f'Floor Selected: {self.floor}')
        time.sleep(2)

        # Search Parameters
        input_search = self.driver.find_element(By.XPATH, "//button[text() = 'Search']")
        input_search.click()
        time.sleep(2)

        ## Select Seat
        # Formats different: '05 - Primary Individual Open/Primaire, individuel et ouvert' and 'JT08-05 - Secondary Individual/Secondaire et individuel'
        try:
            input_selected_seat = self.driver.find_element(By.XPATH, f"//p[text() = '{self.workstation} - Primary Individual Open/Primaire, individuel et ouvert']")
        except NoSuchElementException:
            input_selected_seat = self.driver.find_element(By.XPATH, f"//p[text() = '{self.floor}-{int(self.workstation):02} - Secondary Individual/Secondaire et individuel']")
        print(f"Seat Selected: {input_selected_seat.text}")
        input_selected_seat.click()
        time.sleep(2)

        # Book Seat
        input_book_seat = self.driver.find_element(By.XPATH, "//button[text() = 'Book']")
        input_book_seat.click()
        time.sleep(2)

        # Book for 'Myself'
        input_book_myself = self.driver.find_element(By.XPATH, "//span[text() = 'Myself']")
        input_book_myself.click()
        time.sleep(2)

        # Booking Seat
        input_book_seat = self.driver.find_element(By.XPATH, "//button[text() = 'BOOK']")
        input_book_seat.click()

        # Confirmation page
        self.popups()
        input_confirmation = self.driver.find_element(By.XPATH, "//button[text() = 'GO TO MAIN']") # 'logon-sign-in-btn'
        input_confirmation.click()
        print("Confirmation seat is booked")

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
