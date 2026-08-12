-- ============================================================
-- Judicial Auction Crawler — MySQL Schema
-- ============================================================

CREATE DATABASE IF NOT EXISTS judicial_auctions
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE judicial_auctions;

-- ── 1. Reference: courts ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS courts (
    id          TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    code        CHAR(3)          NOT NULL COMMENT 'TPD / PCD / ...',
    name        VARCHAR(40)      NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 2. Main: auction listings (upcoming + completed) ─────────
CREATE TABLE IF NOT EXISTS auctions (
    id              BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,

    -- Case identifiers
    court_code      CHAR(3)          NOT NULL COMMENT 'FK → courts.code',
    court_name      VARCHAR(40)      NOT NULL,
    case_year       SMALLINT         NOT NULL COMMENT 'Gregorian year, e.g. 2026 (民國+1911)',
    case_type       VARCHAR(10)      NOT NULL COMMENT '司執 / 司執全 / ...',
    case_no         VARCHAR(20)      NOT NULL,
    case_division   VARCHAR(10)      NOT NULL DEFAULT '' COMMENT '股別',
    auction_round   TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '拍別 1–15',
    file_name       VARCHAR(200)     DEFAULT NULL COMMENT 'PDF path from API, e.g. /tpd/115.../xxx.pdf',
    para            VARCHAR(200)     DEFAULT NULL COMMENT 'base64 key for detail page (?para=...)',

    -- Sale type
    sale_type       TINYINT          NOT NULL COMMENT '1=一般,4=應買,5=拍定',

    -- Property type
    prop_type       VARCHAR(10)      NOT NULL DEFAULT '' COMMENT 'C51/C52/C103/C54',

    -- Location
    county_no       VARCHAR(5)       DEFAULT NULL,
    county_name     VARCHAR(20)      DEFAULT NULL COMMENT '縣市',
    district        VARCHAR(30)      DEFAULT NULL COMMENT '鄉鎮市區',
    section         VARCHAR(30)      DEFAULT NULL COMMENT '段',

    -- Property details
    address         TEXT             DEFAULT NULL COMMENT '房屋地址 / 土地坐落',
    total_area_ping DECIMAL(12,4)    DEFAULT NULL COMMENT '總面積 (坪)',

    -- Auction info
    auction_date    DATE             DEFAULT NULL COMMENT '拍賣日期',
    reserve_price   BIGINT           DEFAULT NULL COMMENT '最低拍賣底價 (元)',
    hammer_price    BIGINT           DEFAULT NULL COMMENT '拍定價格 (元, saletype=5)',

    -- Status flags
    delivery_yn     CHAR(1)          DEFAULT NULL COMMENT '點交 Y/N',
    vacant_yn       CHAR(1)          DEFAULT NULL COMMENT '空屋/空地 Y/N',
    remote_bid_yn   CHAR(1)          DEFAULT NULL COMMENT '通訊投標 Y/N',
    contamination   VARCHAR(20)      DEFAULT NULL COMMENT '土地污染 area code',

    -- Upload timestamp from source
    upload_date     DATE             DEFAULT NULL COMMENT 'Upload date (Gregorian, converted from 民國)',
    upload_time     CHAR(6)          DEFAULT NULL COMMENT 'HHMMSS',

    -- Full raw JSON row from QUERY.htm response
    raw_json        JSON             DEFAULT NULL,

    -- Housekeeping
    first_seen_at   DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP
                                     ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_auction (court_code, case_year, case_type, case_no,
                           auction_round, sale_type),
    KEY idx_auction_date  (auction_date),
    KEY idx_court         (court_code),
    KEY idx_sale_type     (sale_type),
    KEY idx_prop_type     (prop_type),
    KEY idx_county        (county_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 3. Detail + PDF per auction ───────────────────────────────
CREATE TABLE IF NOT EXISTS auction_details (
    id              BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
    auction_id      BIGINT UNSIGNED  NOT NULL,

    -- PDF
    pdf_url         TEXT             DEFAULT NULL,
    pdf_local_path  TEXT             DEFAULT NULL COMMENT 'relative to PDF_DIR',
    pdf_text        LONGTEXT         DEFAULT NULL COMMENT 'pdfplumber extracted text',
    pdf_json        JSON             DEFAULT NULL COMMENT 'structured fields from PDF',

    -- Full raw JSON from detail endpoint
    detail_raw_json JSON             DEFAULT NULL,

    fetched_at      DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_detail_auction (auction_id),
    CONSTRAINT fk_detail_auction
        FOREIGN KEY (auction_id) REFERENCES auctions (id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 4. Crawler run audit log ──────────────────────────────────
CREATE TABLE IF NOT EXISTS crawler_runs (
    id              INT UNSIGNED     NOT NULL AUTO_INCREMENT,
    run_type        VARCHAR(20)      NOT NULL COMMENT 'upcoming / historical / detail',
    court_code      CHAR(3)          DEFAULT NULL COMMENT 'NULL = all courts',
    sale_type       VARCHAR(5)       DEFAULT NULL,
    prop_type       VARCHAR(10)      DEFAULT NULL,
    date_from       DATE             DEFAULT NULL,
    date_to         DATE             DEFAULT NULL,

    started_at      DATETIME         NOT NULL,
    finished_at     DATETIME         DEFAULT NULL,
    records_found   INT              DEFAULT 0,
    records_new     INT              DEFAULT 0,
    records_updated INT              DEFAULT 0,
    status          VARCHAR(10)      DEFAULT NULL COMMENT 'running/success/error',
    error_text      TEXT             DEFAULT NULL,

    PRIMARY KEY (id),
    KEY idx_run_started (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── Seed courts reference table ───────────────────────────────
INSERT IGNORE INTO courts (code, name) VALUES
    ('TPD', '臺灣臺北地方法院'),
    ('PCD', '臺灣新北地方法院'),
    ('SLD', '臺灣士林地方法院'),
    ('TYD', '臺灣桃園地方法院'),
    ('SCD', '臺灣新竹地方法院'),
    ('MLD', '臺灣苗栗地方法院'),
    ('TCD', '臺灣臺中地方法院'),
    ('NTD', '臺灣南投地方法院'),
    ('CHD', '臺灣彰化地方法院'),
    ('ULD', '臺灣雲林地方法院'),
    ('CYD', '臺灣嘉義地方法院'),
    ('TND', '臺灣臺南地方法院'),
    ('CTD', '臺灣橋頭地方法院'),
    ('KSD', '臺灣高雄地方法院'),
    ('PTD', '臺灣屏東地方法院'),
    ('TTD', '臺灣臺東地方法院'),
    ('HLD', '臺灣花蓮地方法院'),
    ('ILD', '臺灣宜蘭地方法院'),
    ('KLD', '臺灣基隆地方法院'),
    ('PHD', '臺灣澎湖地方法院'),
    ('KMD', '福建金門地方法院'),
    ('LCD', '福建連江地方法院');
