-- PytesSerial MariaDB initialization
-- Creates the `pytes` database and the `pwr_data` table.
-- Intended for new PytesSerial v2.x installations.

CREATE DATABASE IF NOT EXISTS `pytes`
    DEFAULT CHARACTER SET utf8
    COLLATE utf8_general_ci;

USE `pytes`;

CREATE TABLE IF NOT EXISTS `pwr_data` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `record_time` datetime NOT NULL DEFAULT current_timestamp(),
    `power` int(11) NOT NULL,
    `voltage` float NOT NULL,
    `current` float NOT NULL,
    `temperature` decimal(11,0) NOT NULL,
    `soc` int(11) NOT NULL,
    `basic_st` varchar(11) NOT NULL,
    `volt_st` varchar(11) DEFAULT NULL,
    `current_st` varchar(11) DEFAULT NULL,
    `temp_st` varchar(11) DEFAULT NULL,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
