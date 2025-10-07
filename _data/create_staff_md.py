from csv import DictReader
import re
from yaml import load, dump
from google_drive_downloader import GoogleDriveDownloader as gdd
import os.path
from PIL import Image

"""
The purpose of this script is to generate the 2 .yml files for tas + tutors
to display on the course website. Steps:

1. Install the packages in requirements.txt

2. Convert staff responses into a separate spreadsheet with just the following
   information (must be done before invoking this script):

        a. E-mail
        b. Name
        c. Bio
        d. Appointment ('ta' or 'tutor' or 'ai')
        e. Link to photo on google drive (make sure sharing is set to 'Anyone with link')
        f. Pronouns
        g. Link to personal website

3. Download .csv and place in this directory.

4. Invoke this script which will ask for the .csv filename, which then downloads
   all the images to the assets directory and updates the .yml files

NOTE: If we keep repeatedly trying, Google Drive will pick up and temporarily
network ban you from accessing the photos, so be aware of that.
NOTE: If an image is not showing up, verify that underlying filetype is correct. If the issue persists, rerun the script.

@author: onk

"""

IMG_ID_PATTERN = r'((?:\w|-){33})'

long_line = '-' * 50

csv_file_name = "staff.csv"

email = "Email Address"
name = "Full Name"
bio = "Bio"
appointment = "Appointment"
photo_link = "Photo"
pronouns = "Pronouns"
website_link = "Personal Website"
staff_email_access = "Staff Email Access"
dsp_data_access = "DSP Data Access"
student_support_data_access = "Student Support Data Access"

required_columns = [email, name, bio, appointment, photo_link, pronouns, website_link, 
                   staff_email_access, dsp_data_access, student_support_data_access]

def crop_to_square(image_path):
    """Crops an image to be square around its center."""
    try:
        with Image.open(image_path) as img:
            # Convert from PNG to RGB if necessary
            img = img.convert('RGB')
            
            width, height = img.size
            if width == height:
                return  # Already square
            
            new_size = min(width, height)
            left = (width - new_size) // 2
            top = (height - new_size) // 2
            right = left + new_size
            bottom = top + new_size
            
            # Crop and save
            cropped = img.crop((left, top, right, bottom))
            cropped.save(image_path, quality=95)
    except Exception as e:
        print(f"Error cropping image {image_path}: {str(e)}")

with open(csv_file_name, newline='') as csvfile:
    reader = DictReader(csvfile)
    # Validate that all required columns exist
    missing_columns = [col for col in required_columns if col not in reader.fieldnames]
    if missing_columns:
        print("Error: The following required columns are missing from the CSV:")
        for col in missing_columns:
            print(f"- {col}")
        exit(1)
        
    # Check for extraneous columns
    extra_columns = [col for col in reader.fieldnames if col not in required_columns]
    if extra_columns:
        print("\nWarning: The following columns are not required and will be ignored:")
        for col in extra_columns:
            print(f"- {col}")
        print("\nYou may want to remove these columns from your CSV file to keep it clean.")
        print(long_line)

    for row in reader:
        md = '---\n'
        staff_member = {}
        staff_member['email'] = row[email]
        staff_member['name'] = row[name]
        staff_member['bio'] = row[bio]

        # Flexible appointment handling
        raw_appointment = row[appointment].lower()
        if 'head' in raw_appointment:
            staff_type = 'head'
        elif 'ta' in raw_appointment:
            staff_type = 'ta'
        elif 'tutor' in raw_appointment:
            staff_type = 'tutor'
        elif 'ai' in raw_appointment:
            staff_type = 'ai'
        else:
            print(f"Warning: Unknown appointment type '{raw_appointment}' for {row[name]}")
            staff_type = 'unknown'

        gdrive_link = row[photo_link]
        _name = staff_member['name']

        staff_member['photo'] = None
        staff_member['pronouns'] = row[pronouns]

        # Add https:// if not already present at start of staff_member['link']
        if 'link' in staff_member and not (row[website_link].startswith('http') or row[website_link].startswith('https')):
            staff_member['link'] = 'https://' + row[website_link]
        else:
            staff_member['link'] = row[website_link] or ''

        md += 'name: ' + _name + '\n'
        md += 'pronouns: ' + staff_member['pronouns'] + '\n'
        md += 'role: ' + staff_type + '\n'
        md += 'email: ' + staff_member['email'] + '\n'
        md += 'website: ' + str(staff_member['link']) + '\n'

        # Add relevant tags
        if row[staff_email_access].lower() == "yes":
            md += 'staffEmailAccess: yes\n'
        if row[dsp_data_access].lower() == "yes":
            md += 'dspDataAccess: yes\n'
        if row[student_support_data_access].lower() == "yes":
            md += 'studentSupportDataAccess: yes\n'

        hyphenated_name = _name.lower().replace(' ', '-')
        img_path = f'{hyphenated_name}-1.jpg'
        full_img_path = os.path.join(os.getcwd(), os.pardir, 'assets/', 'staff/', img_path)

        staff_member['photo'] = img_path
        if os.path.exists(full_img_path):
            print(f'Skipping existing image for {_name}')
        else:
            if re.findall(IMG_ID_PATTERN, gdrive_link) == []:
                print(f'Bad link for {_name}, not downloading image: {gdrive_link}')
            else:
                img_id = re.findall(IMG_ID_PATTERN, gdrive_link)[0]
                try:
                    gdd.download_file_from_google_drive(
                        file_id=img_id,
                        dest_path=os.path.join(os.getcwd(), os.pardir, 'assets/', 'staff/', img_path),
                        overwrite=True,
                    )
                    
                    # Crop the downloaded image to square
                    crop_to_square(full_img_path)

                    print(gdrive_link)
                except:
                    print(f"Gdrive photo could not be accessed for {row[name]}")

        md += 'photo: ' + img_path + '\n'
        md += '---' + '\n\n'
        md += staff_member['bio'] 
        file_name = hyphenated_name + '.md'
        file_path = os.path.join(os.getcwd(), os.pardir, '_staffers/', file_name)
        with open(file_path, 'w') as file:
            file.write(md)
