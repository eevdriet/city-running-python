#!/usr/bin/env python3
"""
pip3 install garth requests readchar

export EMAIL=<your garmin email>
export PASSWORD=<your garmin password>

"""
import datetime
import os
from getpass import getpass

import gpxpy
import requests
from garminconnect import Garmin, GarminConnectAuthenticationError
from garth.exc import GarthHTTPError

from crunner.common import AREA_IDS, RUNS_PATH
from crunner.gpx import add_total_distance, strip_gpx

# Load environment variables if defined
tokenstore = "~/.local/share/garminconnect"
tokenstore_base64 = "~/.local/share/garminconnect_base64"
api = None


def get_credentials():
    """Get user credentials."""

    email = input("Login e-mail: ")
    password = getpass("Enter password: ")

    return email, password


def get_mfa():
    """Get MFA."""

    return input("MFA one-time code: ")


def init_api():
    """Initialize Garmin API with your credentials."""

    try:
        # Using Oauth1 and OAuth2 token files from directory
        print(
            f"Trying to login to Garmin Connect using token data from directory '{tokenstore}'...\n"
        )

        garmin = Garmin()
        garmin.login(tokenstore)

    except (FileNotFoundError, GarthHTTPError, GarminConnectAuthenticationError):
        # Session is expired. You'll need to log in again
        print(
            "Login tokens not present, login with your Garmin Connect credentials to generate them.\n"
            f"They will be stored in '{tokenstore}' for future use.\n"
        )
        try:
            # Ask for credentials if not set as environment variables
            email, password = get_credentials()

            garmin = Garmin(
                email=email, password=password, is_cn=False, prompt_mfa=get_mfa
            )
            garmin.login()
            # Save Oauth1 and Oauth2 token files to directory for next login
            garmin.garth.dump(tokenstore)
            print(
                f"Oauth tokens stored in '{tokenstore}' directory for future use. (first method)\n"
            )
            # Encode Oauth1 and Oauth2 tokens to base64 string and safe to file for next login (alternative way)
            token_base64 = garmin.garth.dumps()
            dir_path = os.path.expanduser(tokenstore_base64)
            with open(dir_path, "w") as token_file:
                token_file.write(token_base64)
            print(
                f"Oauth tokens encoded as base64 string and saved to '{dir_path}' file for future use. (second method)\n"
            )
        except (
            FileNotFoundError,
            GarthHTTPError,
            GarminConnectAuthenticationError,
            requests.exceptions.HTTPError,
        ) as err:
            print(err)
            return None

    return garmin


# Main program loop


def download_activities(show_downloaded: bool = False):
    while True:
        query = f"""
Please enter the area(s) to update (separate with ,):
{"\n".join(f"\t- {prefix} ({region})" for prefix, region in AREA_IDS.items())}
or write all to update all areas 
or press Q to quit
"""
        response = input(query)
        if response.lower() == "q":
            return

        if response.lower() == "all":
            ids = AREA_IDS.keys()
            break

        if response not in AREA_IDS:
            chosen = [id.strip() for id in response.split(",")]
            if any(id in AREA_IDS for id in chosen):
                ids = [id for id in chosen if id in AREA_IDS]
                break
            else:
                print("Sorry, try again...")
                continue

        ids = [response]
        break

    api = init_api()
    if api is None:
        return

    for id in ids:
        area = AREA_IDS[id]
        prefix = f"{id} - "

        print(f"Updating {area}...")

        # Let's say we want to scrape all activities using switch menu_option "p". We change the values of the below variables, IE startdate days, limit,...
        today = datetime.date.today()
        startdate = today - datetime.timedelta(weeks=70)  # Select past week

        activities = api.get_activities_by_date(
            startdate.isoformat(), today.isoformat(), "running"
        )
        for activity in activities:
            # Only consider activities with the correct prefix
            name: str = activity["activityName"]
            if not name.startswith(prefix):
                continue

            name = name.removeprefix(prefix)
            activity["activityName"] = name

            # Avoid duplicate downloads
            dir = RUNS_PATH / area

            if any(
                path.is_file() and name.startswith(path.stem) for path in dir.iterdir()
            ):
                if show_downloaded:
                    print(f"\t- {name} (already downloaded)")
                continue

            # Download the GPX data and strip it from all statistics except for lat/lng and first/final time stamps
            gpx_bytes = api.download_activity(
                activity["activityId"], dl_fmt=api.ActivityDownloadFormat.GPX
            )

            gpx = gpxpy.parse(gpx_bytes.decode("utf-8"))
            gpx = strip_gpx(gpx)
            add_total_distance(gpx, "km")

            print(f"\t- {name}")
            with open(dir / f"{name}.gpx", "w") as file:
                file.write(gpx.to_xml())


def main():
    download_activities()


if __name__ == "__main__":
    main()
