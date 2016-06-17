import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

url = 'http://www.google.com'
#profile = webdriver.FirefoxProfile(r'C:\Users\jesse\AppData\Roaming\Mozilla\Firefox\Profiles\s4ft55oj.default')
#browser = webdriver.Firefox(profile)
browser = webdriver.Firefox()
print("Getting "+url)
browser.get(url)

search = browser.find_element_by_name('q')
search.send_keys("hillary clinton c")
#search.send_keys(Keys.RETURN) # hit return after you enter search text
time.sleep(5) # sleep for 5 seconds so you can see the results
browser.quit()