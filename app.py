
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import pandas as pd
from googlesearch import search
from urllib.parse import urlparse

# Initialize Flask and Database
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///resultss.db'  # SQLite database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Define database model
class SearchResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=True)
    link = db.Column(db.String(500), nullable=True)
    website = db.Column(db.String(500), nullable=True)
    stars = db.Column(db.Float, nullable=True)
    reviews = db.Column(db.Integer, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    facebook = db.Column(db.String(500), nullable=True)  # Added column
    instagram = db.Column(db.String(500), nullable=True)  # Added column
    linkedin = db.Column(db.String(500), nullable=True)  # Added column
    twitter = db.Column(db.String(500), nullable=True)  # Added column



# Initialize the database
with app.app_context():
    db.create_all()


# Function to save results to the database
def save_to_database(results):
    for data in results:
        result = SearchResult(
            title=data.get('title'),
            link=data.get('link'),
            website=data.get('website'),
            stars=data.get('stars'),
            reviews=data.get('reviews'),
            phone=data.get('phone'),
            facebook=data.get('facebook'),
            instagram=data.get('instagram'),
            linkedin=data.get('linkedin'),
            twitter=data.get('twitter')
        )
        db.session.add(result)
    db.session.commit()


# Function to search for social media links based on business name
def search_social_media(business_name):
    # Perform Google search for the business name
    search_results = search(business_name, num_results=10)

    # Initialize a dictionary to store social media links
    social_media_links = {
        "Business Name": business_name,
        "Facebook": None,
        "Instagram": None,
        "LinkedIn": None,
        "Twitter": None
    }

    for url in search_results:
        # Parse the URL to extract domain
        parsed_url = urlparse(url)
        domain_name = parsed_url.netloc

        # Check if the URL contains a social media domain
        for domain, platform in social_media_domains.items():
            if domain in domain_name:
                social_media_links[platform] = url

    return social_media_links


# List of known social media domains
social_media_domains = {
    "facebook.com": "Facebook",
    "instagram.com": "Instagram",
    "linkedin.com": "LinkedIn",
    "twitter.com": "Twitter"
}


# Function to scrape results from Google Maps
def scrape_results(keyword):
    driver = webdriver.Chrome()  # Correct driver initialization
    driver.get(f'https://www.google.com/maps/search/{keyword}/')

    # Handle possible pop-ups
    try:
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "form:nth-child(2)"))).click()
    except Exception:
        pass

    scrollable_div = driver.find_element(By.CSS_SELECTOR, 'div[role="feed"]')
    driver.execute_script("""
        var scrollableDiv = arguments[0];
        function scrollWithinElement(scrollableDiv) {
            return new Promise((resolve, reject) => {
                var totalHeight = 0;
                var distance = 1000;
                var scrollDelay = 3000;
                var timer = setInterval(() => {
                    var scrollHeightBefore = scrollableDiv.scrollHeight;
                    scrollableDiv.scrollBy(0, distance);
                    totalHeight += distance;

                    if (totalHeight >= scrollHeightBefore) {
                        totalHeight = 0;
                        setTimeout(() => {
                            var scrollHeightAfter = scrollableDiv.scrollHeight;
                            if (scrollHeightAfter > scrollHeightBefore) {
                                return;
                            } else {
                                clearInterval(timer);
                                resolve();
                            }
                        }, scrollDelay);
                    }
                }, 200);
            });
        }
        return scrollWithinElement(scrollableDiv);
    """, scrollable_div)

    items = driver.find_elements(By.CSS_SELECTOR, 'div[role="feed"] > div > div[jsaction]')

    results = []
    for item in items:
        data = {}

        try:
            data['title'] = item.find_element(By.CSS_SELECTOR, ".fontHeadlineSmall").text
        except Exception:
            pass

        try:
            data['link'] = item.find_element(By.CSS_SELECTOR, "a").get_attribute('href')
        except Exception:
            pass

        try:
            data['website'] = item.find_element(By.CSS_SELECTOR,
                                                'div[role="feed"] > div > div[jsaction] div > a').get_attribute('href')
        except Exception:
            pass

        try:
            rating_text = item.find_element(By.CSS_SELECTOR, '.fontBodyMedium > span[role="img"]').get_attribute(
                'aria-label')
            rating_numbers = [float(piece.replace(",", ".")) for piece in rating_text.split(" ") if
                              piece.replace(",", ".").replace(".", "", 1).isdigit()]
            if rating_numbers:
                data['stars'] = rating_numbers[0]
                data['reviews'] = int(rating_numbers[1]) if len(rating_numbers) > 1 else 0
        except Exception:
            pass

        try:
            text_content = item.text
            phone_pattern = r'((\+?\d{1,2}[ -]?)?(\(?\d{3}\)?[ -]?\d{3,4}[ -]?\d{4}|\(?\d{2,3}\)?[ -]?\d{2,3}[ -]?\d{2,3}[ -]?\d{2,3}))'
            matches = re.findall(phone_pattern, text_content)
            phone_numbers = [match[0] for match in matches]
            unique_phone_numbers = list(set(phone_numbers))
            data['phone'] = unique_phone_numbers[0] if unique_phone_numbers else None
        except Exception:
            pass

        if data.get('title'):
            # Now add social media links
            social_links = search_social_media(data['title'])
            data['facebook'] = social_links.get("Facebook")
            data['instagram'] = social_links.get("Instagram")
            data['linkedin'] = social_links.get("LinkedIn")
            data['twitter'] = social_links.get("Twitter")
            results.append(data)

    save_to_database(results)
    driver.quit()


# Route to handle user input and display results
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        keyword = request.form['keyword']
        scrape_results(keyword)
        return redirect(url_for('index'))

    # Fetch results from the database
    results = SearchResult.query.all()
    return render_template('index.html', results=results)


if __name__ == "__main__":
    app.run(debug=True)
