import os
from dotenv import load_dotenv

load_dotenv()

PDF_DIR = os.getenv("JUDICIAL_YUAN_PDF_DIR", "./data/raw/judicial_yuan/pdfs")

_BASE      = "https://aomp109.judicial.gov.tw/judbp/wkw/WHD1A02"
FRAMESET_URL = f"{_BASE}.htm"          # outermost frameset — loads session cookies
FORM_URL     = f"{_BASE}/V1.htm"       # search form — provides CSRF token
RESULTS_URL  = f"{_BASE}/V2.htm"       # results frame — provides `token` field
SEARCH_URL   = f"{_BASE}/QUERY.htm"    # JSON data endpoint

DETAIL_URL      = "https://kpic.judicial.gov.tw/judkp/wkw/WHD1A02_DETAIL/V1.htm"
# PDF flow: VIEW.htm validates the filenm, then DO_VIEWPDF.htm streams the bytes.
PDF_VIEW_URL    = f"{_BASE}/VIEW.htm"        # GET ?filenm=<path> → JSON {data.path, data.file_ext_name}
PDF_DOWNLOAD_URL = f"{_BASE}/DO_VIEWPDF.htm" # GET ?filenm=<path> → application/pdf bytes

REQUEST_DELAY    = float(os.getenv("JUDICIAL_YUAN_REQUEST_DELAY", "0.8"))
REQUEST_TIMEOUT  = int(os.getenv("JUDICIAL_YUAN_REQUEST_TIMEOUT", "30"))

UPCOMING_DAYS_AHEAD  = int(os.getenv("JUDICIAL_YUAN_UPCOMING_DAYS_AHEAD", "90"))
HISTORICAL_DAYS_BACK = int(os.getenv("JUDICIAL_YUAN_HISTORICAL_DAYS_BACK", "365"))

# 22 courts: (code, name)
COURTS = [
    ("TPD", "臺灣臺北地方法院"),
    ("PCD", "臺灣新北地方法院"),
    ("SLD", "臺灣士林地方法院"),
    ("TYD", "臺灣桃園地方法院"),
    ("SCD", "臺灣新竹地方法院"),
    ("MLD", "臺灣苗栗地方法院"),
    ("TCD", "臺灣臺中地方法院"),
    ("NTD", "臺灣南投地方法院"),
    ("CHD", "臺灣彰化地方法院"),
    ("ULD", "臺灣雲林地方法院"),
    ("CYD", "臺灣嘉義地方法院"),
    ("TND", "臺灣臺南地方法院"),
    ("CTD", "臺灣橋頭地方法院"),
    ("KSD", "臺灣高雄地方法院"),
    ("PTD", "臺灣屏東地方法院"),
    ("TTD", "臺灣臺東地方法院"),
    ("HLD", "臺灣花蓮地方法院"),
    ("ILD", "臺灣宜蘭地方法院"),
    ("KLD", "臺灣基隆地方法院"),
    ("PHD", "臺灣澎湖地方法院"),
    ("KMD", "福建金門地方法院"),
    ("LCD", "福建連江地方法院"),
]

# property type codes as used in the form
PROP_TYPES = ["C52", "C51", "C103", "C54"]

# sale type codes: 1=normal auction, 4=buy notice, 5=hammer price (completed)
SALE_TYPE_UPCOMING   = ["1", "4"]
SALE_TYPE_HISTORICAL = ["5"]

PAGE_SIZE = 100
