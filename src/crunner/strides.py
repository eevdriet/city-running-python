import datetime
import json
import re
import time
from collections import Counter
from itertools import count

import requests
from attrs import define
from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.common.exceptions import (NoSuchElementException,
                                        StaleElementReferenceException)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from crunner.common import STREET_PATH
from crunner.path import Paths

CITY_IDS = {"Rotterdam": 124926}
USER_IDS = {"eevdriet": 59909}


@define
class Activity:
    date: datetime.date
    distance: float
    completed: int
    progressed: int

    @classmethod
    def from_json(cls, d: dict):
        d["date"] = datetime.date.fromisoformat(d["date"])

        return cls(*d.values())

    def to_json(self):
        return {
            "date": self.date.isoformat(),
            "distance": self.distance,
            "completed": self.completed,
            "progressed": self.progressed,
        }


class CityStrides:
    URL_USER_STREETS = "https://citystrides.com/users/{user_id}"
    URL_CITY_USER_STREETS = "https://citystrides.com/users/{user_id}/cities/{city_id}"
    URL_CITY_STREETS = "https://citystrides.com/cities/{city_id}"

    STREET_BUTTON_XPATH = "//a[normalize-space(text())='5315']"
    # NEXT_BUTTON_XPATH = "//nav[@aria-label='Street list']//button[last()]"
    STREET_BUTTON_XPATH = "//nav[@class='flex -mb-px'][1]//a[{button_idx}]"
    ACTIVITY_BUTTON_XPATH = "//nav[@aria-label='Activity list']//form//button"
    STREET_LIST_XPATH = '//div[@data-controller="streets"]'
    NEXT_BUTTON_XPATH = f"{STREET_LIST_XPATH}//button[normalize-space(text())='Next']"

    def __init__(self):
        self.driver: webdriver.Firefox = self.get_driver(headless=False)

    def scroll_to(self, el):
        self.driver.execute_script("arguments[0].scrollIntoView(true);", el)

    def find_leaderboard_streets(self):
        URL = "https://citystrides.com/leaderboard"

        # Verify whether the city page is reachable
        res = requests.get(URL)
        if res.status_code != 200:
            print(f"The requested URL {URL} was invalid, skipping...")
            return

        # Find all completed activities and how many streets were completed/progressed
        self.driver.get(URL)

        streets = self.__find_leaderboard_streets()
        if streets:
            with open(Paths.runs() / "leaderboard.json", "w", encoding="utf-8") as file:
                json.dump(streets, file, indent=4)

    def __find_leaderboard_streets(self) -> list[Activity]:
        streets = []

        def get_next_form(page: int):
            # XPATH = f"//form[@action='/users/{user_id}/search_activities?context={user_id}-activities&amp;page={page}']"
            XPATH = f"//form[@action='/users/search?context=leaderboard&page={page}']"

            for _ in range(20):
                try:
                    next_form = self.driver.find_element(By.XPATH, XPATH)
                    break
                except:
                    print(f"Could not find form from XPATH '{XPATH}', trying again...")
                    continue
            else:
                return None

            return next_form

        for page in count(1):
            print(page)

            try:
                XPATH = f"//turbo-frame[@id='leaderboard']"
                leaderboard_el = self.driver.find_element(By.XPATH, XPATH)
                leaderboard_html = leaderboard_el.get_attribute("outerHTML")
                leaderboard = BeautifulSoup(leaderboard_html, "html.parser")
                street_matches = leaderboard.find_all(
                    string=lambda text: text is not None and "streets" in text.lower()
                )

                for street_match in street_matches:
                    re_match = re.search(r"(\d+) (?:total )?streets", street_match)
                    if re_match:
                        streets.append(int(re_match[1]))

                next_form = get_next_form(page + 1)
                if next_form is None:
                    break

                next_form.submit()

            except NoSuchElementException:
                print(f"No next button found, exiting...")
                break
            except StaleElementReferenceException:
                """
                button class="relative inline-flex items-center rounded-md bg-white dark:bg-zinc-900 px-3 py-2 text-sm font-semibold text-zinc-900 dark:text-zinc-200 ring-1 ring-inset ring-zinc-300 dark:ring-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800" type="submit">
                """
                next_form = get_next_form(page + 1)
                if next_form is None:
                    break

                next_form.submit()
                page += 1

        return streets

    def find_activity_streets(self, user: str = "eevdriet"):
        # Get the user to find streets for or myself
        user_id = USER_IDS.get(user)

        if not user_id:
            print(f"City and/or user were invalid")
            return

        # Verify whether the city/user page is reachable
        URL = self.URL_USER_STREETS.format(user_id=user_id)

        # Verify whether the city page is reachable
        res = requests.get(URL)
        if res.status_code != 200:
            print(f"The requested URL {URL} was invalid, skipping...")
            return

        # Find all completed activities and how many streets were completed/progressed
        self.driver.get(URL)

        activities = self.__find_activities(user_id)
        if activities:
            with open(
                Paths.runs() / "city-strides.json", "w", encoding="utf-8"
            ) as file:
                json.dump([a.to_json() for a in activities], file, indent=4)

    def find_user_streets(self, city: str, user: str = "eevdriet"):
        # Get the user to find streets for or myself
        city_id = CITY_IDS.get(city)
        user_id = USER_IDS.get(user)

        if not city_id or not user_id:
            print(f"City and/or user were invalid: {city_id} / {user_id}")
            return

        STRIDES_PATH = STREET_PATH / city / "city_strides"

        # Verify whether the city/user page is reachable
        URL = self.URL_CITY_USER_STREETS.format(user_id=user_id, city_id=city_id)

        # Verify whether the city page is reachable
        res = requests.get(URL)
        if res.status_code != 200:
            print(f"The requested URL {URL} was invalid, skipping...")
            return

        # Find all streets that are still to be done
        self.driver.get(URL)
        XPATH = self.STREET_BUTTON_XPATH.format(button_idx=1)

        streets = self.__find_streets_form(XPATH, city_id, user_id, complete=False)
        if streets:
            with open(STRIDES_PATH / "todo.json", "w", encoding="utf-8") as file:
                json.dump(streets, file, indent=4)

        # Find all streets that are already completed
        self.driver.get(URL)
        XPATH = self.STREET_BUTTON_XPATH.format(button_idx=2)

        streets = self.__find_streets_form(XPATH, city_id, user_id, complete=True)
        if streets:
            with open(STRIDES_PATH / "completed.json", "w", encoding="utf-8") as file:
                json.dump(streets, file, indent=4)

    def find_streets(self, city: str):
        city_id = CITY_IDS.get(city)
        if city_id is None:
            print(f"City {city} could not be retrieved")
            return

        URL = self.URL_CITY_STREETS.format(city_id=city_id)
        STRIDES_PATH = STREET_PATH / city / "city_strides"

        # Verify whether the city page is reachable
        res = requests.get(URL)
        if res.status_code != 200:
            print(f"The requested URL {URL} was invalid, skipping...")
            return

        # If the page is valid, go there
        self.driver.get(URL)

        XPATH = self.STREET_BUTTON_XPATH.format(button_idx=2)
        streets = self.__find_streets(XPATH)
        print(len(streets))

        with open(STRIDES_PATH / "all.json", "w", encoding="utf-8") as file:
            json.dump(streets, file, indent=4)

    def get_driver(self, headless: bool = True) -> webdriver.Firefox:
        options = webdriver.FirefoxOptions()
        options.headless = headless

        return webdriver.Firefox(options=options)

    def __find_activities(self, user_id: int) -> list[Activity]:
        activities = []

        def get_next_form(page: int):
            # XPATH = f"//form[@action='/users/{user_id}/search_activities?context={user_id}-activities&amp;page={page}']"
            XPATH = f"//form[@action='/users/{user_id}/search_activities?context={user_id}-activities&page={page}']"

            for _ in range(10):
                try:
                    next_form = self.driver.find_element(By.XPATH, XPATH)
                    break
                except:
                    print(f"Could not find form from XPATH '{XPATH}', trying again...")
                    continue
            else:
                return None

            return next_form

        page = 1
        while True:
            self.driver.implicitly_wait(3)
            print(page)

            try:
                XPATH = f"//div[@id='activities']"
                activities_el = self.driver.find_element(By.XPATH, XPATH)
                activities_html = activities_el.get_attribute("outerHTML")
                activities_div = BeautifulSoup(activities_html, "html.parser")
                activities_divs = list(
                    activities_div.find_all("a", id=re.compile(r"^activity_"))
                )

                for idx, activity_el in enumerate(activities_divs, start=1):
                    try:
                        date_str = activity_el.find("h2").text.strip()
                        date = datetime.datetime.strptime(date_str, "%B %d, %Y").date()

                        # Get the distance (2nd <div> inside first "flex items-center..." container)
                        distance_str = activity_el.select_one(
                            ".items-center div"
                        ).text.strip()
                        distance = float(re.match(r"\d+.\d+", distance_str)[0])

                        # Get the "Completed" and "Progressed" numbers by span ID
                        completed = int(
                            activity_el.find(
                                "span", id=lambda x: x and x.endswith("-completed")
                            ).text.strip()
                        )

                        progressed = int(
                            activity_el.find(
                                "span", id=lambda x: x and x.endswith("-progressed")
                            ).text.strip()
                        )

                        activity = Activity(date, distance, completed, progressed)
                        activities.append(activity)

                    except:
                        print(
                            f"Couldn't find all properties for activity {idx} on page {page}"
                        )
                        continue

                next_form = get_next_form(page + 1)
                if next_form is None:
                    break

                next_form.submit()
                page += 1

            except NoSuchElementException:
                print(f"No next button found, exiting...")
                break
            except StaleElementReferenceException:
                """
                button class="relative inline-flex items-center rounded-md bg-white dark:bg-zinc-900 px-3 py-2 text-sm font-semibold text-zinc-900 dark:text-zinc-200 ring-1 ring-inset ring-zinc-300 dark:ring-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800" type="submit">
                """
                next_form = get_next_form(page + 1)
                if next_form is None:
                    break

                next_form.submit()
                page += 1

        return activities

    def __find_streets_form(
        self, xpath: str, city_id: int, user_id: int, complete: bool = True
    ) -> list[str]:
        # Find the street button and click it
        STREET_BUTTON_XPATH = self.STREET_BUTTON_XPATH.format(button_idx=2)
        complete_str = "complete" if complete else "incomplete"

        try:
            streets_button = self.driver.find_element(By.XPATH, xpath)
            self.__wait_for_clickable(STREET_BUTTON_XPATH)
            streets_button.click()
            pass
        except NoSuchElementException:
            print(f"No street button found, exiting...")
            return []

        def get_next_form(page: int):
            XPATH = f"//form[@action='/streets/search?context=city_{complete_str}-{city_id}-{user_id}&page={page}']"

            for _ in range(10):
                try:
                    next_form = self.driver.find_element(By.XPATH, XPATH)
                    break
                except:
                    print("Could not find form, trying again...")
                    continue
            else:
                return None

            return next_form

        streets = set()

        page = 1
        while True:
            self.driver.implicitly_wait(1)
            print(page)

            try:
                XPATH = f"//turbo-frame[@id='city_{complete_str}-{city_id}-{user_id}']"
                streets_el = self.driver.find_element(By.XPATH, XPATH)
                streets_html = streets_el.get_attribute("outerHTML")
                streets_div = BeautifulSoup(streets_html, "html.parser")
                streets_divs = list(
                    streets_div.find_all("div", id=re.compile(r"^street"))
                )

                for street_el in streets_divs:
                    divs = street_el.find_all("div")
                    if len(divs) == 0:
                        print("Couldn't find 1st <div>s, skipping...")
                        continue

                    divs = divs[0].find_all("div")
                    if len(divs) == 0:
                        print("Couldn't find 2st <div>s, skipping...")
                        continue

                    street = divs[0].get_text(strip=True)
                    streets.add(street)

                next_form = get_next_form(page + 1)
                if next_form is None:
                    break

                next_form.submit()
                page += 1

            except NoSuchElementException:
                print(f"No next button found, exiting...")
                break
            except StaleElementReferenceException:
                """
                button class="relative inline-flex items-center rounded-md bg-white dark:bg-zinc-900 px-3 py-2 text-sm font-semibold text-zinc-900 dark:text-zinc-200 ring-1 ring-inset ring-zinc-300 dark:ring-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800" type="submit">
                """
                next_form = get_next_form(page + 1)
                if next_form is None:
                    break

                next_form.submit()
                page += 1

        streets = list(streets)
        streets.sort()

        return streets

    def __find_streets(self, xpath: str) -> list[str]:
        # Find the street button and click it
        STREET_BUTTON_XPATH = self.STREET_BUTTON_XPATH.format(button_idx=2)
        try:
            streets_button = self.driver.find_element(By.XPATH, xpath)
            self.__wait_for_clickable(STREET_BUTTON_XPATH)
            streets_button.click()
            self.__scroll_to(streets_button)
            self.driver.implicitly_wait(10)
        except NoSuchElementException:
            print(f"No street button found, exiting...")
            return []

        def get_next_button():
            XPATH = '//button[@class="relative inline-flex items-center rounded-md bg-white dark:bg-zinc-900 px-3 py-2 text-sm font-semibold text-zinc-900 dark:text-zinc-200 ring-1 ring-inset ring-zinc-300 dark:ring-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800"]'
            # buttons = self.driver.find_elements(By.XPATH, self.NEXT_BUTTON_XPATH)
            buttons = self.driver.find_elements(By.XPATH, XPATH)
            if len(buttons) == 0:
                return None

            return buttons[0] if len(buttons) == 1 else buttons[1]

        streets = set()

        page = 0
        while True:
            print(page)

            try:
                streets_el = self.driver.find_element(By.XPATH, self.STREET_LIST_XPATH)
                streets_html = streets_el.get_attribute("outerHTML")
                streets_div = BeautifulSoup(streets_html, "html.parser")

                for street_el in streets_div.find_all("div", id=re.compile(r"^street")):
                    divs = street_el.find_all("div")
                    if len(divs) == 0:
                        print("Couldn't find 1st <div>s, skipping...")
                        continue

                    divs = divs[0].find_all("div")
                    if len(divs) == 0:
                        print("Couldn't find 2st <div>s, skipping...")
                        continue

                    street = divs[0].get_text(strip=True)
                    streets.add(street)

                next_button = get_next_button()
                if next_button is None:
                    break

                self.__wait_for_clickable(self.NEXT_BUTTON_XPATH)
                next_button.click()
                page += 1

            except NoSuchElementException:
                print(f"No next button found, exiting...")
                return
            except StaleElementReferenceException:
                """
                button class="relative inline-flex items-center rounded-md bg-white dark:bg-zinc-900 px-3 py-2 text-sm font-semibold text-zinc-900 dark:text-zinc-200 ring-1 ring-inset ring-zinc-300 dark:ring-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800" type="submit">
                """
                next_button = get_next_button()
                if next_button is None:
                    break

                self.__wait_for_clickable(self.NEXT_BUTTON_XPATH)
                next_button.click()
                page += 1

        streets = list(streets)
        streets.sort()

        return streets

    def __scroll_to(self, el):
        self.driver.execute_script("arguments[0].scrollIntoView(true);", el)

    def __wait_for_clickable(self, xpath: str):
        return WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )


def main():
    finder = CityStrides()
    finder.find_leaderboard_streets()


if __name__ == "__main__":
    main()
