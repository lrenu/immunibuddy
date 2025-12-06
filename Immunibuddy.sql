
CREATE DATABASE IF NOT EXISTS immunibuddy;
USE immunibuddy;

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('parent','provider','admin') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE child (
    child_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    dob DATE NOT NULL,
    passport_number VARCHAR(50),
    current_country VARCHAR(100),
    parent_mailid VARCHAR(100),
    parent_primary_mobile_no VARCHAR(30),
    user_id INT,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE TABLE vaccine (
    vaccine_id INT AUTO_INCREMENT PRIMARY KEY,
    vaccine_name VARCHAR(100) NOT NULL,
    doses_required INT NOT NULL,
    min_age_months INT,
    dose_interval_days INT,
    is_travel TINYINT(1) DEFAULT 0
);

CREATE TABLE vaccination_record (
    record_id INT AUTO_INCREMENT PRIMARY KEY,
    child_id INT NOT NULL,
    vaccine_id INT NOT NULL,
    dose_number INT NOT NULL,
    date_given DATE NOT NULL,
    country_given VARCHAR(100),
    clinic_unique_name VARCHAR(100),
    FOREIGN KEY (child_id) REFERENCES child(child_id) ON DELETE CASCADE,
    FOREIGN KEY (vaccine_id) REFERENCES vaccine(vaccine_id) ON DELETE CASCADE
);

CREATE TABLE travel (
    trip_id INT AUTO_INCREMENT PRIMARY KEY,
    child_id INT NOT NULL,
    destination_country VARCHAR(100) NOT NULL,
    travel_date DATE NOT NULL,
    return_date DATE,
    risk_level VARCHAR(50),
    required_vaccines_json TEXT,
    advisory_note TEXT,
    FOREIGN KEY (child_id) REFERENCES child(child_id) ON DELETE CASCADE
);

CREATE TABLE qr_access (
    qr_id INT AUTO_INCREMENT PRIMARY KEY,
    child_id INT NOT NULL,
    qr_code_hash VARCHAR(128) NOT NULL UNIQUE,
    created_date DATETIME NOT NULL,
    expiry_date DATETIME NOT NULL,
    access_count INT DEFAULT 0,
    is_active TINYINT(1) DEFAULT 1,
    FOREIGN KEY (child_id) REFERENCES child(child_id) ON DELETE CASCADE
);

CREATE TABLE verification_log (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    provider_id INT,
    child_id INT,
    qr_id INT,
    status VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (provider_id) REFERENCES users(user_id),
    FOREIGN KEY (child_id) REFERENCES child(child_id),
    FOREIGN KEY (qr_id) REFERENCES qr_access(qr_id)
);



SET SQL_SAFE_UPDATES = 0;

USE immunibuddy;
DELETE FROM users WHERE role IN ('admin', 'provider');

INSERT INTO users (name, email, password, role) VALUES
('Admin User', 'admin@immunibuddy.com', 'scrypt:32768:8:1$es3LsNuY9s3AYdRN$cce0a130e42ee4389ba08e9cfcc47f88b42577a1fc042b49932b2ec900553473cb67bb388717a2bbb551dbea88f88fef0368aea0ae1ac64d787a728478bce1f9', 'admin'),
('Dr. Provider', 'provider@immunibuddy.com', 'scrypt:32768:8:1$es3LsNuY9s3AYdRN$cce0a130e42ee4389ba08e9cfcc47f88b42577a1fc042b49932b2ec900553473cb67bb388717a2bbb551dbea88f88fef0368aea0ae1ac64d787a728478bce1f9', 'provider');

SELECT qr_code_hash FROM qr_access;

SELECT vaccine_id, vaccine_name FROM vaccine WHERE is_travel = 1;

INSERT INTO country_vaccine_req (country, vaccine_id) VALUES
('Japan', 7), ('Japan', 8),
('India', 7), ('India', 8), ('India', 10),
('Brazil', 7), ('Brazil', 8),
('Thailand', 7), ('Thailand', 8), ('Thailand', 10),
('Kenya', 7), ('Kenya', 8),
('Nigeria', 7), ('Nigeria', 8);

USE immunibuddy;

-- Get parent user_id first (use your parent account)
SET @parent_id = (SELECT user_id FROM users WHERE role='parent' LIMIT 1);

-- Add more children
INSERT INTO child (name, dob, passport_number, current_country, parent_mailid, parent_primary_mobile_no, user_id) VALUES
('Ben', '2019-05-15', 'B789012', 'USA', 'parent@test.com', '9876543210', @parent_id),
('Clara', '2021-08-20', 'C345678', 'UK', 'parent@test.com', '9876543210', @parent_id);

-- Add vaccination records for Anna (child_id=1)
INSERT INTO vaccination_record (child_id, vaccine_id, dose_number, date_given, country_given, clinic_unique_name) VALUES
(1, 1, 1, '2020-12-15', 'USA', 'City Hospital'),
(1, 2, 1, '2021-01-10', 'USA', 'City Hospital'),



USE immunibuddy;

-- Get child IDs for Ben and Clara
SET @ben_id = (SELECT child_id FROM child WHERE name='Ben' LIMIT 1);
SET @clara_id = (SELECT child_id FROM child WHERE name='Clara' LIMIT 1);

-- Vaccinations for Ben
INSERT INTO vaccination_record (child_id, vaccine_id, dose_number, date_given, country_given, clinic_unique_name) VALUES
(@ben_id, 1, 1, '2019-06-01', 'USA', 'Metro Hospital'),
(@ben_id, 2, 1, '2019-07-15', 'USA', 'Metro Hospital'),
(@ben_id, 3, 1, '2019-09-01', 'USA', 'Metro Hospital'),
(@ben_id, 5, 1, '2020-05-15', 'USA', 'Kids Care'),
(@ben_id, 7, 1, '2023-01-10', 'USA', 'Travel Clinic');

-- Vaccinations for Clara
INSERT INTO vaccination_record (child_id, vaccine_id, dose_number, date_given, country_given, clinic_unique_name) VALUES
(@clara_id, 1, 1, '2021-09-01', 'UK', 'NHS Clinic'),
(@clara_id, 2, 1, '2021-10-20', 'UK', 'NHS Clinic'),
(@clara_id, 3, 1, '2021-12-15', 'UK', 'NHS Clinic');

-- Travel plans for Ben
INSERT INTO travel (child_id, destination_country, travel_date, return_date) VALUES
(@ben_id, 'Japan', '2026-03-01', '2026-03-15'),
(@ben_id, 'Kenya', '2026-08-10', '2026-08-25');

-- Travel plans for Clara
INSERT INTO travel (child_id, destination_country, travel_date, return_date) VALUES
(@clara_id, 'India', '2026-02-01', '2026-02-14'),
(@clara_id, 'Brazil', '2026-07-01', '2026-07-20');
(1, 3, 1, '2021-03-01', 'USA', 'Kids Clinic'),
(1, 5, 1, '2021-12-01', 'USA', 'Kids Clinic');

-- Add travel plans
INSERT INTO travel (child_id, destination_country, travel_date, return_date) VALUES
(1, 'India', '2026-01-15', '2026-01-30'),
(1, 'Thailand', '2026-06-01', '2026-06-15');


Select * from users;