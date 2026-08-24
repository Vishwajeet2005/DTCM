-- ---------------------------------------------------------------------------
-- db/init.sql
-- MySQL-compatible DDL for Digital Twin CO2 Monitor (DTCM).
--
-- Run with:
--   mysql -u <user> -p <database> < db/init.sql
--
-- Tables are created in dependency order so FK constraints can be
-- validated immediately.
-- ---------------------------------------------------------------------------

SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------------------------------------------------------
-- 1. SensorData
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `SensorData` (
    `sensor_id`         INT            NOT NULL AUTO_INCREMENT,
    `location`          VARCHAR(255)   NOT NULL,
    `type`              VARCHAR(100)   DEFAULT NULL,
    `installation_date` DATE           DEFAULT NULL,
    `status`            VARCHAR(50)    NOT NULL DEFAULT 'Active',
    PRIMARY KEY (`sensor_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 2. EnvironmentalData
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `EnvironmentalData` (
    `data_id`     INT        NOT NULL AUTO_INCREMENT,
    `sensor_id`   INT        NOT NULL,
    `co2_level`   DOUBLE     NOT NULL,
    `temperature` DOUBLE     DEFAULT NULL,
    `humidity`    DOUBLE     DEFAULT NULL,
    `pm25`        DOUBLE     DEFAULT NULL,
    `aqi`         DOUBLE     DEFAULT NULL,
    `timestamp`   DATETIME   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `data_gap`    TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (`data_id`),
    INDEX `ix_envdata_timestamp` (`timestamp`),
    INDEX `ix_envdata_sensor_id` (`sensor_id`),
    CONSTRAINT `fk_envdata_sensor`
        FOREIGN KEY (`sensor_id`)
        REFERENCES `SensorData` (`sensor_id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 3. Users
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `Users` (
    `user_id`       INT          NOT NULL AUTO_INCREMENT,
    `name`          VARCHAR(255) NOT NULL,
    `email`         VARCHAR(255) NOT NULL,
    `role`          VARCHAR(50)  NOT NULL,
    `password_hash` VARCHAR(255) DEFAULT NULL,
    `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`user_id`),
    UNIQUE KEY `uq_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 4. PredictionResults
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `PredictionResults` (
    `prediction_id`   INT          NOT NULL AUTO_INCREMENT,
    `data_id`         INT          DEFAULT NULL,
    `predicted_co2`   DOUBLE       DEFAULT NULL,
    `model_used`      VARCHAR(100) DEFAULT NULL,
    `confidence_low`  DOUBLE       DEFAULT NULL,
    `confidence_high` DOUBLE       DEFAULT NULL,
    `prediction_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`prediction_id`),
    CONSTRAINT `fk_pred_envdata`
        FOREIGN KEY (`data_id`)
        REFERENCES `EnvironmentalData` (`data_id`)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 5. SimulationResults
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `SimulationResults` (
    `sim_id`           INT          NOT NULL AUTO_INCREMENT,
    `scenario_name`    VARCHAR(255) DEFAULT NULL,
    `simulated_co2`    DOUBLE       DEFAULT NULL,
    `parameters`       JSON         DEFAULT NULL,
    `sim_time`         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `baseline_co2`     DOUBLE       DEFAULT NULL,
    `reduction_pct`    DOUBLE       DEFAULT NULL,
    `hourly_forecast`  JSON         DEFAULT NULL,
    PRIMARY KEY (`sim_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 6. Alerts
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `Alerts` (
    `alert_id`   INT          NOT NULL AUTO_INCREMENT,
    `data_id`    INT          DEFAULT NULL,
    `sensor_id`  INT          DEFAULT NULL,
    `alert_type` VARCHAR(100) DEFAULT NULL,
    `message`    TEXT         DEFAULT NULL,
    `alert_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `status`     VARCHAR(50)  NOT NULL DEFAULT 'Active',
    PRIMARY KEY (`alert_id`),
    CONSTRAINT `fk_alert_envdata`
        FOREIGN KEY (`data_id`)
        REFERENCES `EnvironmentalData` (`data_id`)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 7. Thresholds
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `Thresholds` (
    `threshold_id`       INT    NOT NULL AUTO_INCREMENT,
    `sensor_id`          INT    NOT NULL,
    `warning_threshold`  DOUBLE NOT NULL DEFAULT 450.0,
    `critical_threshold` DOUBLE NOT NULL DEFAULT 500.0,
    PRIMARY KEY (`threshold_id`),
    UNIQUE KEY `uq_thresholds_sensor` (`sensor_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------------
-- Seed Data
-- ---------------------------------------------------------------------------

-- Default sensors
INSERT INTO `SensorData` (`location`, `type`, `installation_date`, `status`) VALUES
    ('Downtown Core',        'NDIR CO2 Sensor', CURDATE(), 'Active'),
    ('Industrial Zone North','NDIR CO2 Sensor', CURDATE(), 'Active'),
    ('Residential East',     'NDIR CO2 Sensor', CURDATE(), 'Active'),
    ('Green Park West',      'NDIR CO2 Sensor', CURDATE(), 'Active'),
    ('Traffic Hub Central',  'NDIR CO2 Sensor', CURDATE(), 'Active');

-- Default per-sensor thresholds (sensor IDs 1-5 from above INSERT)
INSERT INTO `Thresholds` (`sensor_id`, `warning_threshold`, `critical_threshold`) VALUES
    (1, 450.0, 500.0),
    (2, 450.0, 500.0),
    (3, 450.0, 500.0),
    (4, 450.0, 500.0),
    (5, 450.0, 500.0);

-- Default admin user
-- NOTE: Replace the password_hash value below with the bcrypt hash of the
--       desired admin password before running in production.
--       Example hash shown is for the password 'Admin@1234' (cost=12).
--       Generate a fresh hash with Python:
--           import bcrypt
--           print(bcrypt.hashpw(b'Admin@1234', bcrypt.gensalt(12)).decode())
INSERT INTO `Users` (`name`, `email`, `role`, `password_hash`, `created_at`) VALUES
    (
        'System Admin',
        'admin@dtcm.local',
        'administrator',
        -- bcrypt hash placeholder: replace with a freshly generated hash
        '$2b$12$REPLACE_WITH_REAL_BCRYPT_HASH_OF_Admin@1234',
        NOW()
    );
