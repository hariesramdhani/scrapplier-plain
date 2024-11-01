import time

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from tqdm.notebook import tqdm
import undetected_chromedriver as uc

class Scraper:
    """
    Base class for scraping data from different supplier websites.
    
    Attributes:
    - username: Username for logging into the supplier website.
    - password: Password for logging into the supplier website.
    - headless: Whether to run the scraper in headless mode.
    """

    def __init__(self, username, password, headless=False):
        self.headless = headless
        self.username = username
        self.password = password
        self.driver = uc.Chrome(headless=self.headless, use_subprocess=False)

    def _login_monkhouse(self, driver):
        """
        Logs into the Monkhouse website.

        Args:
        - driver: The Selenium WebDriver instance.
        """
        close_button = driver.find_element(By.ID, 'lpclose')
        close_button.click()
        accept_button = driver.find_element(By.ID, 'onetrust-accept-btn-handler')
        accept_button.click()

        email_input = driver.find_element(By.NAME, 'login[username]')
        email_input.send_keys(username)
        password_input = driver.find_element(By.NAME, 'login[password]')
        password_input.send_keys(password)
        submit_button = driver.find_element(By.ID, 'send2')
        submit_button.click()

        print("Successfully logged into Monkhouse.")

    def _scrape_monkhouse(self, driver, depth="schools"):
        """
        Scrapes data from the Monkhouse website.

        Args:
        - driver: The Selenium WebDriver instance.
        - depth: The depth to scrape data at. Can be "schools", "products" or "variants".
        """
        
        driver.get('https://www.monkhouse.com/customer/account/login/')
        time.sleep(10)

        self._login_monkhouse(driver)

        driver.get("https://www.monkhouse.com/school")
        elements = driver.find_elements(By.CSS_SELECTOR, '.search-results ul li a')

        schools = []

        for element in tqdm(elements):
            school = {}
            school["store_page"] = element.get_attribute('href')
            school["raw_name"] = element.text

            if "URN-" in school["raw_name"]:
                school["urn"] = school["raw_name"].split("URN-")[1][:-1]
            else:
                school["urn"] = None
            schools.append(school)

        pd.DataFrame(schools).to_csv("monkhouse_schools.csv", index=False)

        if depth == "schools":
            print("Successfully scraped schools.")
            return 0

        product_id = 0
        products = []

        for i, school in tqdm(enumerate(schools)):
            school["schoolsupplier_id"] = i
            driver.get(school["store_page"])

            # Wait for the page to load
            WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.products.list.items.product-items'))
            )

            try:
                # Click "Load More" until all products are loaded
                while True:
                    try:
                        load_more_button = driver.find_element(By.CSS_SELECTOR, '.action.show-more')
                        load_more_button.click()
                    except:
                        break

                main_element = driver.find_element(By.CSS_SELECTOR, '.products.list.items.product-items')
                product_elements = main_element.find_elements(By.CSS_SELECTOR, '.item.product.product-item')
            except:
                school["products"] = None
                break

            for product_element in product_elements:
                product = {}
                try:
                    product["schoolsupplier_id"] = i
                    product["id"] = product_id

                    product_id += 1
                    product["name"] = product_element.find_element(By.CSS_SELECTOR, '.product-item-link').get_attribute('text')
                    product["link"] = product_element.find_element(By.CSS_SELECTOR, '.product-item-link').get_attribute('href')
                    product["price"] = product_element.find_element(By.CSS_SELECTOR, '.price').text
                    product["image"] = product_element.find_element(By.CSS_SELECTOR, '.product-image-photo').get_attribute('src')
                    try:
                        product["label"] = product_element.find_element(By.CSS_SELECTOR, '.product-label>span').text
                    except:
                        product["label"] = None
                except:
                    continue

                products.append(product)

            school["products"] = products

        pd.DataFrame(products).to_csv("monkhouse_products.csv", index=False)
        
        if depth == "products":
            print("Successfully scraped schools and products.")
            return 0

        variant_id = 0
        variants = []

        for product in tqdm(products):

            driver.get(product["link"])

            # Wait for the page to load
            try:
                WebDriverWait(driver, 1).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.swatch-select.size')))
            except:
                continue

            select_element = Select(driver.find_element(By.CSS_SELECTOR, '.swatch-select.size'))
            options = select_element.options

            for option in options:
                size = option.get_attribute('data-option-label')
                # Select the option
                try:    
                    select_element.select_by_visible_text(option.text)
                    # Get the price
                    price = driver.find_element(By.CSS_SELECTOR, '.price-wrapper ').text

                    description = driver.find_element(By.CSS_SELECTOR, '.product.attribute.description').text

                    description_icons = driver.find_elements(By.CSS_SELECTOR, ".description-icon img")
                    
                    variant = {}
                    variant["id"] = variant_id
                    variant_id += 1
                    variant["product_id"] = product["id"]
                    variant["size"] = size
                    variant["price"] = price
                    variant["description"] = description

                    try:
                        description_icon_alts = []
                        for description_icon in description_icons:
                            if description_icon.get_attribute('alt') != "":
                                description_icon_alts.append(description_icon.get_attribute('alt'))
                        variant["description_icon_alts"] = description_icon_alts
                    except: 
                        variant["description_icon_alts"] = None

                    try:
                        colors = driver.find_elements(By.CSS_SELECTOR, '.swatch-attribute.color')
                        color_options = colors[0].find_elements(By.CSS_SELECTOR, '.swatch-option')
                        color_option_values = []
                        for color_option in color_options:
                            color_option_values.append(color_option.get_attribute('data-option-label'))
                        variant["colors"] = color_option_values
                    except:
                        variant["colors"] = None

                    variants.append(variant)

                except:
                    variant = {}
                    variants.append(variant)

        pd.DataFrame(variants).to_csv("monkhouse_variants.csv", index=False)

        print("Successfully scraped schools, products and variants.")

    def _scrape_blossomsschoolwear(self, driver, depth="schools"):
        """
        Scrapes data from the Blossoms Schoolwear website.

        Args:
        - driver: The Selenium WebDriver instance.
        - depth: The depth to scrape data at. Can be "schools", "products" or "variants

        """

        driver.get('https://blossomsschoolwear.com/nursery-school-uniform/')

        schools = []

        category_urls = [
            'https://blossomsschoolwear.com/nursery-school-uniform/',
        ]

        for category_url in category_urls:
            driver.get(category_url)

            school_elements = driver.find_elements(By.CSS_SELECTOR, '.product-img-list>.text-center')

            for school_element in school_elements:
                school = {}
                school_name = school_element.find_element(By.CSS_SELECTOR, '.header-cat').text
                store_page = school_element.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                
                school['school_name'] = school_name
                school['store_page'] = store_page

                schools.append(school)

        pd.DataFrame(schools).to_csv("blossomsschoolwear_schools.csv", index=False)


        if depth == "schools":
            print("Successfully scraped schools.")
            return 0
        
        products = []
        product_id = 0

        for i, school in enumerate(schools):
            school["schoolsupplier_id"] = i
            store_page_url = f'{school["store_page"]}?limit=100' if '?' not in school["store_page"] else f'{school["store_page"]}&limit=100'

            driver.get(store_page_url)

            product_elements = driver.find_elements(By.CSS_SELECTOR, '.product')

            for product_element in product_elements:
                product = {}
                try:
                    product["schoolsupplier_id"] = i
                    product["id"] = product_id

                    product_id += 1
                    name = product_element.find_element(By.CSS_SELECTOR, 'img').get_attribute('title')
                    price = product_element.find_element(By.CSS_SELECTOR, '.price.price--withoutTax').text
                    url = product_element.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                    image = product_element.find_element(By.CSS_SELECTOR, 'img').get_attribute('src')
                    
                    product['name'] = name
                    product['price'] = price
                    product['url'] = url
                    product['image'] = image
                except:
                    continue
                    
                products.append(product)

            school["products"] = products

        
        pd.DataFrame(products).to_csv("blossomsschoolwear_products.csv", index=False)

        if depth == "products":
            print("Successfully scraped schools and products.")
            return 0

        variant_id = 0
        variants = []

        for product in tqdm(product_df.to_dict(orient="records")):

            driver.get(product["url"])

            # Wait for the page to load
            try:
                WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.form-select.form-select--small')))
            except:
                driver.save_screenshot(f'../data_dirty/error/error_{product["id"]}.png')
                continue

            select_element = Select(driver.find_element(By.CSS_SELECTOR, '.form-select.form-select--small'))
            options = select_element.options

            for option in options:
                size = option.text
                # Select the option
                try:    
                    select_element.select_by_visible_text(option.text)
                    # Get the price
                    time.sleep(0.1)
                    price = driver.find_element(By.CSS_SELECTOR, '.price.price--withoutTax').text

                    description = np.nan

                    description_icons = np.nan
                    
                    variant = {}
                    variant["id"] = variant_id
                    variant_id += 1
                    variant["product_id"] = product["id"]
                    variant["size"] = size
                    variant["price"] = price
                    variant["description"] = description

                    variants.append(variant)

                except:
                    variant = {}
                    variants.append(variant)
            
        pd.DataFrame(variants).to_csv("blossomsschoolwear_variants.csv", index=False)

    
    def _scrape_pinderschoolwear(self, driver, depth="schools"):

        """
        Scrapes data from the Pinders Schoolwear website.

        Args:
        - driver: The Selenium WebDriver instance.
        - depth: The depth to scrape data at. Can be "schools", "products" or "variants
        """

        alphabets = list(map(chr, range(97, 123)))

        schools = []
        for alphabet in alphabets:
            driver.get(f"https://pindersschoolwear.com/schoollist/{alphabet}")

            main_element = driver.find_element(By.CSS_SELECTOR, 'div.page-section div.container > div.row')
            school_elements = main_element.find_elements(By.CSS_SELECTOR, '.product-inner')

            for school_element in school_elements:
                school = {}

                store_page = school_element.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                school_name = school_element.find_element(By.CSS_SELECTOR, '.title').text

                school['name'] = school_name
                school['store_page'] = store_page
                
                schools.append(school)
        
        pd.DataFrame(schools).to_csv("pinderschoolwear_schools.csv", index=False)

        products = []
        product_id = 0

        for i, school in enumerate(schools):
            school["schoolsupplier_id"] = i
            store_page_url = f'{school["store_page"]}?limit=100' if '?' not in school["store_page"] else f'{school["store_page"]}&limit=100'

            driver.get(store_page_url)

            main_element = driver.find_element(By.CSS_SELECTOR, '.row.main-products.product-grid')
            product_elements = main_element.find_elements(By.CSS_SELECTOR, '.product-grid-item')

            for product_element in product_elements:
                product = {}
                try:
                    product["schoolsupplier_id"] = i
                    product["id"] = product_id

                    product_id += 1
                    product["name"] = product_element.find_element(By.CSS_SELECTOR, '.product-details .name a').get_attribute('innerHTML')
                    product["link"] = product_element.find_element(By.CSS_SELECTOR, '.product-details .name a').get_attribute('href')
                    product["price"] = product_element.find_element(By.CSS_SELECTOR, '.product-details .price').text
                    product["image"] = product_element.find_element(By.CSS_SELECTOR, '.product-thumb img').get_attribute('src')
                except:
                    continue
                    
                products.append(product)

            school["products"] = products

        pd.DataFrame(products).to_csv("pinderschoolwear_products.csv", index=False)


    def _scrape_schoolwearmadeeasy(self, driver, depth="schools"):
        """
        Scrapes data from the Schoolwear Made Easy website.

        Args:
        - driver: The Selenium WebDriver instance.
        - depth: The depth to scrape data at. Can be "schools", "products" or "variants
        """

        driver.get('https://schoolwearmadeeasy.com/')

        # Simulate click on Find My School
        find_my_school = driver.find_element(By.CSS_SELECTOR, ".tt-dropdown-toggle")
        find_my_school.click()

        schools = []

        elements = driver.find_elements(By.CSS_SELECTOR, ".nav-multilevel .nav-multilevel__layout ul>li ul li a")

        # Get the href attributes
        for element in elements:
            school = {}
            school_link = element.get_attribute("href")
            school_name = element.get_attribute("innerHTML")

            school["name"] = school_name
            school["store_page"] = school_link

            schools.append(school)

        pd.DataFrame(schools).to_csv("schoolwearmadeeasy_schools.csv", index=False)

        products = []
        product_id = 0

        for i, school in enumerate(schools):
            school["schoolsupplier_id"] = i
            driver.get(school["store_page"])

            # Scroll down slowly to load all products
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            main_elements = driver.find_element(By.CSS_SELECTOR, '.tt-product-listing.row')
            product_elements = main_elements.find_elements(By.CSS_SELECTOR, '.tt-product')

            for product_element in product_elements:
                product = {}
                try:
                    product["schoolsupplier_id"] = i
                    product["id"] = product_id

                    product_id += 1
                    product["name"] = product_element.find_element(By.CSS_SELECTOR, '.tt-title.prod-thumb-title-color a').get_attribute('innerHTML')
                    product["link"] = product_element.find_element(By.CSS_SELECTOR, '.tt-title.prod-thumb-title-color a').get_attribute('href')
                    product["price"] = product_element.find_element(By.CSS_SELECTOR, '.tt-price span').text
                    product["image"] = product_element.find_element(By.CSS_SELECTOR, '.tt-img img').get_attribute('srcset')
                except:
                    continue

                products.append(product)

            school["products"] = products

        pd.DataFrame(products).to_csv("schoolwearmadeeasy_products.csv", index=False)

    def _scrape_scotcrestschool(self, driver, depth="schools"):
        """
        Scrapes data from the Scotcrest School website.

        Args:
        - driver: The Selenium WebDriver instance.
        - depth: The depth to scrape data at. Can be "schools", "products" or "variants
        """

        driver.get('https://scotcrestschools.co.uk/Find-Your-School?limit=50')

        areas = driver.find_elements(By.CSS_SELECTOR, '.refine-image a')
        area_links = [area.get_attribute('href') for area in areas]
        schools = []

        for area_link in area_links:
            driver.get(area_link)

            school_elements = driver.find_elements(By.CSS_SELECTOR, '.refine-image a')
            for school_element in school_elements:
                school = {}

                store_page = school_element.get_attribute('href')
                school_name = school_element.find_element(By.CSS_SELECTOR, '.refine-category-name').text

                school['name'] = school_name
                school['store_page'] = store_page
                
                schools.append(school)

        pd.DataFrame(schools).to_csv("scotcrestschool_schools.csv", index=False)

        products = []
        product_id = 0

        for i, school in enumerate(schools):
            school["schoolsupplier_id"] = i
            store_page_url = f'{school["store_page"]}?limit=100' if '?' not in school["store_page"] else f'{school["store_page"]}&limit=100'

            driver.get(store_page_url)

            main_element = driver.find_element(By.CSS_SELECTOR, '.row.main-products.product-grid')
            product_elements = main_element.find_elements(By.CSS_SELECTOR, '.product-grid-item')

            for product_element in product_elements:
                product = {}
                try:
                    product["schoolsupplier_id"] = i
                    product["id"] = product_id

                    product_id += 1
                    product["name"] = product_element.find_element(By.CSS_SELECTOR, '.product-details .name a').get_attribute('innerHTML')
                    product["link"] = product_element.find_element(By.CSS_SELECTOR, '.product-details .name a').get_attribute('href')
                    product["price"] = product_element.find_element(By.CSS_SELECTOR, '.product-details .price').text
                    product["image"] = product_element.find_element(By.CSS_SELECTOR, '.product-thumb img').get_attribute('src')
                except:
                    continue
                    
                products.append(product)

            school["products"] = products

        product_df = pd.DataFrame(products)
        product_df.to_csv("scotcrestschool_products.csv", index=False)

        variant_id = 0
        variants = []

        for product in tqdm(product_df.to_dict(orient="records")[:5]):

            driver.get(product["link"])

            # Wait for the page to load
            try:
                # Find li inside of the ul .tt-options-swatch and click them
                options = driver.find_elements(By.CSS_SELECTOR, 'div.option-select > ul > li')

                # Get all the data-value attribute from options
                data_values = [option.get_attribute("data-value") for option in options]
                sizes = [option.text for option in options]

                for i, data_value in enumerate(data_values):
                    size = sizes[i]
                    
                    # Click element that has data-value attribute equal to data_value
                    driver.find_element(By.CSS_SELECTOR, f'div.option-select > ul > li[data-value="{data_value}"]').click()
                    
                    price = driver.find_element(By.CSS_SELECTOR, '.product-price').text
                    try:
                        description = driver.find_element(By.CSS_SELECTOR, '#tab-description').text
                    except:
                        description = np.nan
                    description_icons = np.nan
                    
                    variant = {}
                    variant["id"] = variant_id
                    variant_id += 1
                    variant["product_id"] = product["id"]
                    variant["size"] = size
                    variant["price"] = price
                    variant["description"] = description

                    variants.append(variant)

                    # except:
                    #     variant = {}
                    #     variants.append(variant)
                        
                    variants_df = pd.DataFrame(variants)

                    variants_df.to_csv("../data_dirty/scotcrestschool_variants.csv", index=False)
                
            except:
                driver.save_screenshot(f'../data_dirty/error/error_{product["id"]}.png')
                continue

        pd.DataFrame(variants).to_csv("scotcrestschool_variants.csv", index=False)

    def _scrape_stevensons(self, driver, depth="schools"):
        """
        Scrapes data from the Stevensons website.

        Args:
        - driver: The Selenium WebDriver instance.
        - depth: The depth to scrape data at. Can be "schools", "products" or "variants
        """

        driver.get('https://www.stevensons.co.uk/school-finder')

        areas = driver.find_elements(By.CSS_SELECTOR, '.refine-image a')
        area_links = [area.get_attribute('href') for area in areas]

        alphabets = list(map(chr, range(97, 123)))

        schools = []
        for alphabet in alphabets:
            driver.get(f"https://www.stevensons.co.uk/school-finder/{alphabet}")

            try:
                main_element = driver.find_element(By.CSS_SELECTOR, '.row.mt-5.pb-4')
                school_elements = main_element.find_elements(By.CSS_SELECTOR, '.school-card')

                for school_element in school_elements:
                    school = {}

                    store_page = school_element.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                    school_name = school_element.find_element(By.CSS_SELECTOR, 'h3').text

                    school['name'] = school_name
                    school['store_page'] = store_page
                    
                    schools.append(school)
            except:
                pass

        pd.DataFrame(schools).to_csv("stevensons_schools.csv", index=False)

        products = []
        product_id = 0

        for i, school in enumerate(schools):
            school["schoolsupplier_id"] = i
            store_page_url = f'{school["store_page"]}?limit=100' if '?' not in school["store_page"] else f'{school["store_page"]}&limit=100'

            driver.get(store_page_url)

            main_element = driver.find_element(By.CSS_SELECTOR, '.row.main-products.product-grid')
            product_elements = main_element.find_elements(By.CSS_SELECTOR, '.product-grid-item')

            for product_element in product_elements:
                product = {}
                try:
                    product["schoolsupplier_id"] = i
                    product["id"] = product_id

                    product_id += 1
                    product["name"] = product_element.find_element(By.CSS_SELECTOR, '.product-details .name a').get_attribute('innerHTML')
                    product["link"] = product_element.find_element(By.CSS_SELECTOR, '.product-details .name a').get_attribute('href')
                    product["price"] = product_element.find_element(By.CSS_SELECTOR, '.product-details .price').text
                    product["image"] = product_element.find_element(By.CSS_SELECTOR, '.product-thumb img').get_attribute('src')
                except:
                    continue
                    
                products.append(product)

            school["products"] = products

        pd.DataFrame(products).to_csv("stevensons_products.csv", index=False)

    def _scrape_alansantryschoolwear(self, driver, depth="schools"):
        """
        Scrapes data from the Alan Santry Schoolwear website.

        Args:
        - driver: The Selenium WebDriver instance.
        - depth: The depth to scrape data at. Can be "schools", "products" or "variants
        """

        driver.get('https://www.alansantryschoolwear.co.uk/')

        product_categories_main = driver.find_element(By.CSS_SELECTOR, '.grid_4.last')
        product_categories_list = [li for li in product_categories_main.find_elements(By.TAG_NAME, 'li')]
        schools = []
        for li in product_categories_list:
            school = {}

            school_name = li.find_element(By.CSS_SELECTOR, 'a').get_attribute('innerText')
            school_link = li.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')

            school['school_name'] = school_name
            school['store_page'] = school_link

            schools.append(school)

        pd.DataFrame(schools).to_csv("alansantryschoolwear_schools.csv", index=False)

        products = []
        product_id = 0

        for i, school in enumerate(schools):
            school["schoolsupplier_id"] = i
            store_page_url = f'{school["store_page"]}'

            driver.get(store_page_url)

            try:
                main_element = driver.find_element(By.CSS_SELECTOR, '#productfilter_items')
                product_elements = main_element.find_elements(By.CSS_SELECTOR, '.grid_3')

                for product_element in product_elements:
                    product = {}
                    try:
                        product["schoolsupplier_id"] = i
                        product["id"] = product_id

                        product_id += 1
                        product["name"] = product_element.find_element(By.CSS_SELECTOR, 'h3 > a').get_attribute('innerText')
                        product["link"] = product_element.find_element(By.CSS_SELECTOR, 'h3 > a').get_attribute('href')
                        product["price"] = product_element.find_element(By.CSS_SELECTOR, '.currencyPrice').text
                        product["image"] = product_element.find_element(By.CSS_SELECTOR, 'img').get_attribute('src')
                    except:
                        continue
                    
                    products.append(product)
            
            except:
                continue


            school["products"] = products

        pd.DataFrame(products).to_csv("alansantryschoolwear_products.csv", index=False)


    def _scrape_aspireacademyglasgow(self, driver, depth="schools"):
        """
        Scrapes data from the Aspire Academy Glasgow website.
        """

        driver.get('https://aspireacademyglasgow.com/')

        # Find element by text "Badged Uniforms"
        badged_uniforms = driver.find_element(By.XPATH, '//*[contains(text(), "Badged Uniforms")]')

        # Click on the element
        badged_uniforms.click()
        product_categories_main = driver.find_element(By.CSS_SELECTOR, '.sub-menu.elementor-nav-menu--dropdown.sm-nowrap')
        product_categories_list = [li for li in product_categories_main.find_elements(By.TAG_NAME, 'li')]
        schools = []
        for li in product_categories_list:
            school = {}

            school_name = li.find_element(By.CSS_SELECTOR, 'a').get_attribute('innerText')
            school_link = li.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')

            school['school_name'] = school_name
            school['store_page'] = school_link

            schools.append(school)

        schools = schools[2:]

        pd.DataFrame(schools).to_csv("aspireacademyglasgow_schools.csv", index=False)

        products = []
        product_id = 0

        for i, school in enumerate(schools):
            school["schoolsupplier_id"] = i
            store_page_url = f'{school["store_page"]}'

            driver.get(store_page_url)

            try:
                main_element = driver.find_element(By.CSS_SELECTOR, '.jet-listing-grid__items')
                product_elements = main_element.find_elements(By.CSS_SELECTOR, '.elementor-container')

                for product_element in product_elements:
                    product = {}
                    try:
                        product["schoolsupplier_id"] = i
                        product["id"] = product_id

                        product_id += 1
                        product["name"] = product_element.find_element(By.CSS_SELECTOR, 'h2 > a').get_attribute('innerText')
                        product["link"] = product_element.find_element(By.CSS_SELECTOR, 'h2 > a').get_attribute('href')
                        product["price"] = product_element.find_element(By.CSS_SELECTOR, '.woocommerce-Price-amount.amount').text
                        product["image"] = product_element.find_element(By.CSS_SELECTOR, 'img').get_attribute('src')
                    except:
                        continue
                    
                    products.append(product)
            
            except:
                continue


            school["products"] = products

        pd.DataFrame(products).to_csv("aspireacademyglasgow_products.csv", index=False)

    
    def _scrape_borderembroideries(self, driver, depth="schools"):

        driver.get('https://www.border-embroideries.co.uk/school-search.html')

        # Find element that contains innertext show all
        show_all = driver.find_element(By.XPATH, '//label[contains(text(), "Show all") and @class="letter"]')
        show_all.click()
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
        school_list_main = driver.find_element(By.CSS_SELECTOR, '.school-list')
        school_list = [elem for elem in school_list_main.find_elements(By.CSS_SELECTOR, '.school')]
        schools = []
        for li in school_list:
            school = {}

            school_name = li.find_element(By.CSS_SELECTOR, 'a').get_attribute('innerText')
            school_link = li.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')

            school['school_name'] = school_name
            school['store_page'] = school_link

            schools.append(school)

        pd.DataFrame(schools).to_csv("borderembroideries_schools.csv", index=False)

        products = []
        product_id = 0

        for i, school in enumerate(schools):
            school["schoolsupplier_id"] = i
            store_page_url = f'{school["store_page"]}'

            driver.get(store_page_url)

            try:
                try:
                    show_more_button = driver.find_element(By.XPATH, '//div[@class="amscroll-load-button" and @amscroll_type="after"]')
                    show_more_button.click()
                except:
                    pass

                main_elements = driver.find_elements(By.CSS_SELECTOR, '.products.wrapper.grid.products-grid')
                for main_element in main_elements:
                    product_elements = main_element.find_elements(By.CSS_SELECTOR, '.item.product')

                    for product_element in product_elements:
                        product = {}
                        try:
                            product["schoolsupplier_id"] = i
                            product["id"] = product_id

                            product_id += 1
                            product["name"] = product_element.find_element(By.CSS_SELECTOR, '.product-item-link').get_attribute('innerText')
                            product["link"] = product_element.find_element(By.CSS_SELECTOR, '.product-item-link').get_attribute('href')
                            product["price"] = product_element.find_element(By.CSS_SELECTOR, '.price').text
                            product["image"] = product_element.find_element(By.CSS_SELECTOR, 'img.img-thumbnail').get_attribute('src')
                        except:
                            continue
                        
                        products.append(product)
            
            except:
                continue


            school["products"] = products
        
        product_df = pd.DataFrame(products)
        product_df.to_csv("borderembroideries_products.csv", index=False)

        variant_id = 0
        variants = []

        for product in tqdm(product_df.to_dict(orient="records")[:5]):

            driver.get(product["link"])

            # Wait for the page to load
            try:
                WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.swatch-select.size')))
            except:
                driver.save_screenshot(f'../data_dirty/error/error_{product["id"]}.png')
                continue

            select_element = Select(driver.find_element(By.CSS_SELECTOR, '.swatch-select.size'))
            options = select_element.options

            for option in options:
                size = option.text
                # Select the option
                try:    
                    select_element.select_by_visible_text(option.text)
                    # Get the price
                    price = driver.find_element(By.CSS_SELECTOR, '.price-wrapper ').text

                    description = driver.find_element(By.CSS_SELECTOR, '.value.std').text

                    description_icons = np.nan
                    
                    variant = {}
                    variant["id"] = variant_id
                    variant_id += 1
                    variant["product_id"] = product["id"]
                    variant["size"] = size
                    variant["price"] = price
                    variant["description"] = description

                    variants.append(variant)

                except:
                    variant = {}
                    variants.append(variant)
                    
        variants_df = pd.DataFrame(variants)

        variants_df.to_csv("borderembroideries_variants.csv", index=False)

    def _scrape_directschoolwear(self, driver, depth="schools"):
        
        schools = []
        school_categories = ['primary-schools', 'uk-secondary-schools', 'find-my-international-school']

        for school_category in school_categories:
            driver.get(f'https://directschoolwear.co.uk/find-my-school/{school_category}.html')

            school_list_main = driver.find_element(By.CSS_SELECTOR, '.category-products.sub-category')
            school_list = [elem for elem in school_list_main.find_elements(By.CSS_SELECTOR, '.product-container')]

            for li in school_list:
                school = {}

                school_name = li.find_element(By.CSS_SELECTOR, 'a').get_attribute('innerText')
                school_link = li.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')

                school['school_name'] = school_name
                school['store_page'] = school_link

                schools.append(school)

        pd.DataFrame(schools).to_csv("directschoolwear_schools.csv", index=False)

        products = []
        product_id = 0

        for i, school in enumerate(schools[:2]):
            school["schoolsupplier_id"] = i
            store_page_url = f'{school["store_page"]}?limit=100'

            driver.get(store_page_url)

            try:

                main_element = driver.find_elements(By.CSS_SELECTOR, '.products-grid')
                
                product_elements = main_element.find_elements(By.CSS_SELECTOR, '.grid_3')

                for product_element in product_elements:
                    product = {}
                    try:
                        product["schoolsupplier_id"] = i
                        product["id"] = product_id

                        product_id += 1
                        product["name"] = product_element.find_element(By.CSS_SELECTOR, 'h2 > a').get_attribute('innerText')
                        product["link"] = product_element.find_element(By.CSS_SELECTOR, 'h2 > a').get_attribute('href')
                        product["price"] = product_element.find_element(By.CSS_SELECTOR, '.price').text
                        product["image"] = product_element.find_element(By.CSS_SELECTOR, 'img').get_attribute('src')
                    except:
                        continue
                    
                    products.append(product)
            
            except:
                continue


            school["products"] = products

        pd.DataFrame(products).to_csv("directschoolwear_products.csv", index=False)

    def _scrape_macgregorschoolwear(self, driver, depth="schools"):

        driver.get('https://macgregorschoolwear.co.uk/product-category/')

        product_categories_main = driver.find_element(By.CSS_SELECTOR, 'ul.product-categories')
        product_categories_lis = [li for li in product_categories_main.find_elements(By.TAG_NAME, 'li')]
        schools = []
        for li in product_categories_lis:
            school = {}

            school_name = li.find_element(By.CSS_SELECTOR, 'a').text
            school_link = li.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')

            school['school_name'] = school_name
            school['store_page'] = school_link

            schools.append(school)

        pd.DataFrame(schools).to_csv("macgregorschoolwear_schools.csv", index=False)

        products = []
        product_id = 0

        for i, school in enumerate(schools):
            school["schoolsupplier_id"] = i
            store_page_url = f'{school["store_page"]}'

            driver.get(store_page_url)

            try:
                main_element = driver.find_element(By.CSS_SELECTOR, '.products.columns-3')
                product_elements = main_element.find_elements(By.CSS_SELECTOR, 'li.product.type-product')

                for product_element in product_elements:
                    product = {}
                    try:
                        product["schoolsupplier_id"] = i
                        product["id"] = product_id

                        product_id += 1
                        product["name"] = product_element.find_element(By.CSS_SELECTOR, 'h2.woocommerce-loop-product__title').get_attribute('innerHTML')
                        product["link"] = product_element.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                        product["price"] = product_element.find_element(By.CSS_SELECTOR, '.woocommerce-Price-amount.amount').text
                        product["image"] = product_element.find_element(By.CSS_SELECTOR, 'img').get_attribute('src')
                    except:
                        continue
                    
                    products.append(product)
            
            except:
                continue


            school["products"] = products

        pd.DataFrame(products).to_csv("macgregorschoolwear_products.csv", index=False)

    def _scrape_schooluniformscotland(self, driver, depth="schools"):
        driver.get('https://schooluniformscotland.com/product-category/schools/')

        product_categories_main = driver.find_element(By.CSS_SELECTOR, '.products.columns-5')
        product_categories_list = [li for li in product_categories_main.find_elements(By.TAG_NAME, 'li')]
        schools = []
        for li in product_categories_list:
            school = {}

            school_name = li.find_element(By.CSS_SELECTOR, 'h2').text
            school_link = li.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')

            school['school_name'] = school_name
            school['store_page'] = school_link

            schools.append(school)

        pd.DataFrame(schools).to_csv("schooluniformscotland_schools.csv", index=False)

        products = []
        product_id = 0

        for i, school in enumerate(schools):
            school["schoolsupplier_id"] = i
            store_page_url = f'{school["store_page"]}'

            driver.get(store_page_url)

            try:
                main_element = driver.find_element(By.CSS_SELECTOR, '.products.columns-5')
                product_elements = main_element.find_elements(By.CSS_SELECTOR, 'li.product.type-product')

                for product_element in product_elements:
                    product = {}
                    try:
                        product["schoolsupplier_id"] = i
                        product["id"] = product_id

                        product_id += 1
                        product["name"] = product_element.find_element(By.CSS_SELECTOR, 'h2.woocommerce-loop-product__title').get_attribute('innerHTML')
                        product["link"] = product_element.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                        product["price"] = product_element.find_element(By.CSS_SELECTOR, '.woocommerce-Price-amount.amount').text
                        product["image"] = product_element.find_element(By.CSS_SELECTOR, 'img').get_attribute('src')
                    except:
                        continue
                    
                    products.append(product)
            
            except:
                continue

            school["products"] = products

        pd.DataFrame(products).to_csv("schooluniformscotland_products.csv", index=False)

    def _scrape_smartschoolwear(self, driver, depth="schools"):
        driver.get('https://www.smartschoolwear.co.uk/')

        school_list_mains = driver.find_elements(By.CSS_SELECTOR, 'ul.level1')[:2]
        school_list = []
        for school_list_main in school_list_mains:
            school_list += [elem for elem in school_list_main.find_elements(By.CSS_SELECTOR, '.level2')]

        schools = []
        for li in school_list:
            school = {}

            school_name = li.find_element(By.CSS_SELECTOR, 'a > span').get_attribute('innerHTML')
            school_link = li.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')

            school['school_name'] = school_name
            school['store_page'] = school_link

            schools.append(school)

        pd.DataFrame(schools).to_csv("smartschoolwear_schools.csv", index=False)
        
        products = []
        product_id = 0

        for i, school in enumerate(schools):
            school["schoolsupplier_id"] = i
            store_page_url = f'{school["store_page"]}'

            driver.get(store_page_url)

            try:
                main_element = driver.find_element(By.CSS_SELECTOR, '.products.columns-4')
                product_elements = main_element.find_elements(By.CSS_SELECTOR, '.product')

                for product_element in product_elements:
                    product = {}
                    try:
                        product["schoolsupplier_id"] = i
                        product["id"] = product_id

                        product_id += 1
                        product["name"] = product_element.find_element(By.CSS_SELECTOR, '.woocommerce-loop-product__title').text
                        product["link"] = product_element.find_element(By.CSS_SELECTOR, '.woocommerce-LoopProduct-link').get_attribute('href')
                        product["price"] = product_element.find_element(By.CSS_SELECTOR, '.woocommerce-Price-amount.amount').text
                        product["image"] = product_element.find_element(By.CSS_SELECTOR, 'img').get_attribute('src')
                    except:
                        continue
                    
                    products.append(product)
            
            except:
                continue


            school["products"] = products

        pd.DataFrame(products).to_csv("smartschoolwear_products.csv", index=False)

    def _scrape_topformschoolwear(self, driver, depth="schools"):

        driver.get('https://www.top-form.co.uk/find-your-school/')

        school_list_main = driver.find_element(By.CSS_SELECTOR, '.products.columns-4')
        school_list = [elem for elem in school_list_main.find_elements(By.CSS_SELECTOR, '.product-category')]
        schools = []
        for li in school_list:
            school = {}

            school_name = li.find_element(By.CSS_SELECTOR, 'a').get_attribute('innerText')
            school_link = li.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')

            school['school_name'] = school_name
            school['store_page'] = school_link

            schools.append(school)
        
        pd.DataFrame(schools).to_csv("topformschoolwear_schools.csv", index=False)

        products = []
        product_id = 0

        for i, school in enumerate(schools):
            school["schoolsupplier_id"] = i
            store_page_url = f'{school["store_page"]}'

            driver.get(store_page_url)

            try:
                main_element = driver.find_element(By.CSS_SELECTOR, '.products.columns-4')
                product_elements = main_element.find_elements(By.CSS_SELECTOR, '.product')

                for product_element in product_elements:
                    product = {}
                    try:
                        product["schoolsupplier_id"] = i
                        product["id"] = product_id

                        product_id += 1
                        product["name"] = product_element.find_element(By.CSS_SELECTOR, '.woocommerce-loop-product__title').text
                        product["link"] = product_element.find_element(By.CSS_SELECTOR, '.woocommerce-LoopProduct-link').get_attribute('href')
                        product["price"] = product_element.find_element(By.CSS_SELECTOR, '.woocommerce-Price-amount.amount').text
                        product["image"] = product_element.find_element(By.CSS_SELECTOR, 'img').get_attribute('src')
                    except:
                        continue
                    
                    products.append(product)
            
            except:
                continue


            school["products"] = products
        
        pd.DataFrame(products).to_csv("topformschoolwear_products.csv", index=False)


    def _scrape_uniformdirect(self, driver, depth="schools"):

        schools = []
        school_categories = ['Primary_Schools', 'Secondary_Schools', 'Special_Schools']

        for school_category in school_categories:
            driver.get(f'https://www.uniform-direct.com/acatalog/{school_category}.html')

            school_list_main = driver.find_element(By.CSS_SELECTOR, '.section-list')
            school_list = [elem for elem in school_list_main.find_elements(By.CSS_SELECTOR, '.item')]

            for li in school_list:
                school = {}

                school_name = li.find_element(By.CSS_SELECTOR, 'h2').text
                school_link = li.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')

                school['school_name'] = school_name
                school['store_page'] = school_link

                schools.append(school)
        
        pd.DataFrame(schools).to_csv("uniformdirect_schools.csv", index=False)

        products = []
        product_id = 0

        for i, school in enumerate(schools[:2]):
            school["schoolsupplier_id"] = i
            store_page_url = f'{school["store_page"]}'

            driver.get(store_page_url)

            # try:
            main_element = driver.find_element(By.CSS_SELECTOR, '#FilterResultElements')
            
            product_elements = main_element.find_elements(By.CSS_SELECTOR, '.std-product-details')

            for product_element in product_elements:
                product = {}
                # try:
                product["schoolsupplier_id"] = i
                product["id"] = product_id

                product_id += 1
                product["name"] = product_element.find_element(By.XPATH, '//div[@class="standardSearchText details"]/a/h2').text
                product["link"] = product_element.find_element(By.CSS_SELECTOR, 'div.details > a').get_attribute('href')
                product["price"] = product_element.find_element(By.CSS_SELECTOR, 'span.product-price').text
                product["image"] = product_element.find_element(By.CSS_SELECTOR, 'div.image > div > a > img').get_attribute('src')
                # except:
                #     continue
                
                products.append(product)

            # except:
            #     continue


            school["products"] = products

        pd.DataFrame(products).to_csv("uniformdirect_products.csv", index=False)

    def _scrape_asda(self, driver, depth="schools"):

        driver.get('https://direct.asda.com/george/school/boys-school-uniform/D10M1G1,default,sc.html')

        # Click this button .onetrust-accept-btn-handler
        driver.find_element(By.ID, 'onetrust-accept-btn-handler').click()
        # If not at the bottom of the page, scroll infinitely to load all of the elements, if no added element stop the scrolling
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            WebDriverWait(driver, 10).until(lambda driver: driver.execute_script("return document.body.scrollHeight") > last_height)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # Get all of the .product-mini-outer-container elements
        product_elements = driver.find_elements(By.CLASS_NAME, 'product-mini-outer-container')
        products = []
        for product_element in product_elements:
            try:
                product = {}
                product['name'] = product_element.find_element(By.CSS_SELECTOR, 'a.title').text
                product['price'] = product_element.find_element(By.CSS_SELECTOR, '.product__price-value').text
                product['url'] = product_element.find_element(By.CSS_SELECTOR, 'a.title').get_attribute('href')
                product['image'] = product_element.find_element(By.CSS_SELECTOR, 'img.primary-image').get_attribute('src')
                products.append(product)
            except:
                pass
        products_df = pd.DataFrame(products)

        products_df.to_csv("asda_products.csv", index=False)


    def scrape(self, supplier):
        """
        Main method to scrape data from the specified supplier.
        
        Args:
        - supplier: The supplier to scrape data from.
        """
        if supplier == "monkhouse":
            self._scrape_monkhouse(self.driver)
        elif supplier == "pinderschoolwear":
            self._scrape_pinderschoolwear(self.driver)
        elif supplier == "schoolwearmadeeasy":
            self._scrape_schoolwearmadeeasy(self.driver)
        elif supplier == "scotcrestschool":
            self._scrape_scotcrestschool(self.driver)
        elif supplier == "stevensons":
            self._scrape_stevensons(self.driver)
        elif supplier == "alansantryschoolwear":
            self._scrape_alansantryschoolwear(self.driver)
        elif supplier == "aspireacademyglasgow":
            self._scrape_aspireacademyglasgow(self.driver)
        elif supplier == "borderembroideries":
            self._scrape_borderembroideries(self.driver)
        elif supplier == "directschoolwear":
            self._scrape_directschoolwear(self.driver)
        elif supplier == "macgregorschoolwear":
            self._scrape_macgregorschoolwear(self.driver)
        elif supplier == "schooluniformscotland":
            self._scrape_schooluniformscotland(self.driver)
        elif supplier == "smartschoolwear":
            self._scrape_smartschoolwear(self.driver)
        elif supplier == "topformschoolwear":
            self._scrape_topformschoolwear(self.driver)
        elif supplier == "uniformdirect":
            self._scrape_uniformdirect(self.driver)
        elif supplier == "asda":
            self._scrape_asda(self.driver)
        else:
            raise ValueError("Invalid supplier name.") 
