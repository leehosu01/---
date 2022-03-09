from collections import defaultdict

import chromedriver_autoinstaller
chromedriver_autoinstaller.install()

import pandas
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

opts = Options()
opts.add_argument("--headless")
opts.add_argument("--window-size=1440,900")
opts.add_argument("--incognito")
opts.add_argument("--disable-gpu")
# https://stackoverflow.com/questions/48773031/how-to-prevent-chrome-headless-from-loading-images
# opts.add_argument("--blink-settings=imagesEnabled=false")
user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36"
opts.add_argument("user-agent={0}".format(user_agent))

driver = webdriver.Chrome(options=opts)


# https://stackoverflow.com/a/62907888
js_find_xpath = """
const xpath = function (xpathToExecute) {
    var result = [];
    var nodesSnapshot = document.evaluate(xpathToExecute, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
    for (var i = 0; i < nodesSnapshot.snapshotLength; i++) {
        result.push(nodesSnapshot.snapshotItem(i));
    }
    return result;
}
"""

wait_method = (
    (
        expected_conditions.visibility_of_element_located,
        expected_conditions.visibility_of_all_elements_located,
    ),
    (
        expected_conditions.presence_of_element_located,
        expected_conditions.presence_of_all_elements_located,
    ),
)[0]
def wait_xpath(driver, xpath, timeout=None):
    return WebDriverWait(driver, timeout).until(wait_method[0](("xpath", xpath)))

def wait_and_click(driver, xpath, timeout=None):
    wait_xpath(driver, xpath, timeout)
    driver.find_element("xpath", xpath).click()

driver.get("http://info.nec.go.kr/")
driver.switch_to.frame('main')
wait_and_click(driver, '//*[@id="topmenu"]/ul/li[4]/a', 10)
try: driver.switch_to.frame('main')
except: ... #print("main fail?")
wait_and_click(driver, '//*[@id="gnb"]/div[4]/ul/li[3]/a', 10)
wait_and_click(driver, '//*[@id="electionId1"]', 10)

total_stats = []
for _ in range(17):
    wait_and_click(driver, '//*[@id="cityCode"]', 10)
    webdriver.ActionChains(driver).send_keys(Keys.ARROW_DOWN).perform()
    wait_and_click(driver, '//*[@id="spanSubmit"]', 10)
    stats = defaultdict(float)


    wait_xpath(driver, '//*[@id="table01"]//tr', 10)
    type1 = driver.execute_script(js_find_xpath + f"""
    let result = [];
    for(let I of xpath('//*[@id="table01"]//tr')[0].children)
        result.push(I.innerText);
    return result;
    """ )
    type2 = driver.execute_script(js_find_xpath + f"""
    let result = [];
    for(let I of xpath('//*[@id="table01"]//tr')[2].children)
        result.push(I.innerText);
    return result;
    """ )
    types = type1[:3] + type2[3:-3] + type1[-3:]

    scrolls = driver.execute_script(js_find_xpath + """
    let result = [];
    let all = xpath('//*[@id="table01"]//tr');
    for(let i in all)
        if(i > 3 && i % 2 == 1) {
            let tmp = [];
            for(let I of xpath('//*[@id="table01"]//tr')[i].children)
                tmp.push(I.innerText);
            result.push(tmp);
        }
    return result;
    """ )
    converted = [ I[:1] + [float(x.replace(',','')) for x in I[1:]] for I in scrolls]
    converted = [dict(zip(types, I)) for I in converted]
    stats['cityName']=driver.execute_script(js_find_xpath+"""
return xpath('//*[@id="cityName"]')[0].innerText
""")
    for I in converted:
        for CAND in types[3:-4]:
            if I['개표율'] > 0:
                stats[CAND] += I[CAND] * (100/I['개표율'])
    total_stats.append(stats)

sum_stats = {}
for key in total_stats[0].keys():
    try: sum_stats[key] = sum(stats[key] for stats in total_stats)
    except: ...
total_stats.append(sum_stats)

for stats in total_stats:
    for K in stats.keys():
        try: stats[K] = f"{stats[K]:.0f}"
        except: ...

import datetime 
KST = datetime.timezone(datetime.timedelta(hours=9))
print(datetime.datetime.now(KST).isoformat())
print()
summary = {CAND:sum_stats[CAND] for CAND in type2[3:-4]}
sum_votes = sum(map(int, summary.values()))
for CAND, votes in summary.items():
    print(f"{CAND} : {int(votes)/sum_votes * 100:.2f}%; {votes}")

pandas.DataFrame(total_stats).to_csv("info.csv")