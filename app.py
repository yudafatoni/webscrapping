from flask import Flask, render_template, request, send_file, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import io
import pandas as pd
import tempfile

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def scrape_data(url):
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException
    from bs4 import BeautifulSoup
    import pandas as pd
    import tempfile

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)
    driver.get(url)

    wait = WebDriverWait(driver, 20)  # Maximum wait time of 20 seconds

    all_data = []
    headers = []

    def scrape_table():
        nonlocal headers
        soup = BeautifulSoup(driver.page_source, "html.parser")
        table_container = soup.find('div', class_="table-visualization-container")
        if not table_container:
            print("Tabel dengan class yang ditentukan tidak ditemukan.")
            return False
        
        if not headers:
            header_row = table_container.find('thead')
            if header_row:
                header_row = header_row.find_all('th')
                headers = [header.text.strip() for header in header_row]
            else:
                print("Header tabel tidak ditemukan.")
                return False

        rows = table_container.find_all('tr')
        for row in rows:
            columns = row.find_all('td')
            if columns:
                all_data.append([col.text.strip() for col in columns])
        return True

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#dashboard-container > dashboard-grid > div > div > div.react-grid-item.dashboard-widget-wrapper.widget-auto-height-enabled.cssTransforms.react-resizable-hide.react-resizable > dashboard-widget > div > div > div.body-row-auto.scrollbox > visualization-renderer > div > div')))
        if not scrape_table():
            print("Gagal scraping tabel pada halaman pertama.")
            driver.quit()
            return None
    except TimeoutException:
        print("Waktu tunggu habis. Tabel tidak ditemukan.")
        driver.quit()
        return None

    while True:
        try:
            next_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#dashboard-container > dashboard-grid > div > div > div.react-grid-item.dashboard-widget-wrapper.widget-auto-height-enabled.cssTransforms.react-resizable-hide.react-resizable > dashboard-widget > div > div > div.body-row-auto.scrollbox > visualization-renderer > div > div > div > div > div > ul > li.ant-pagination-next")))
            if 'ant-pagination-disabled' in next_button.get_attribute('class'):
                break
            actions = ActionChains(driver)
            actions.move_to_element(next_button).perform()
            next_button.click()
            
            # Tunggu hingga elemen halaman berikutnya muncul sebelum scraping lagi
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.table-visualization-container tr")))
            
            if not scrape_table():
                print("Gagal scraping tabel pada halaman berikutnya.")
                break
        except (TimeoutException, NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException) as e:
            print(f"Exception during pagination: {e}")
            break

    driver.quit()
    df = pd.DataFrame(all_data, columns=headers)
    
    output = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    with pd.ExcelWriter(output.name, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    
    return output.name



@app.route('/')
def index():
    filename = session.get('filename')
    return render_template('index.html', filename=filename)

@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form['url']
    filename = request.form['output_filename']
    if not filename.endswith('.xlsx'):
        filename += '.xlsx'
    file_path = scrape_data(url)
    if file_path is None:
        flash("Scraping gagal. Pastikan URL dan class name benar.", "danger")
        return redirect(url_for('index'))
    else:
        session['filename'] = filename
        session['file_path'] = file_path
        return redirect(url_for('index'))

@app.route('/download')
def download():
    filename = session.get('filename')
    file_path = session.get('file_path')
    if not filename or not file_path:
        flash("Tidak ada file untuk diunduh.", "danger")
        return redirect(url_for('index'))
    
    return send_file(file_path, download_name=filename, as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


if __name__ == "__main__":
    app.run(debug=True, threaded=True)
