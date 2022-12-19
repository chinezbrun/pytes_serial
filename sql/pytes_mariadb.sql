-- phpMyAdmin SQL Dump
-- version 4.9.7
-- https://www.phpmyadmin.net/
--
-- Gazdă: localhost
-- Timp de generare: oct. 12, 2022 la 09:35 PM
-- Versiune server: 10.3.32-MariaDB
-- Versiune PHP: 7.4.28

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT = 0;
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Bază de date: `pytes`
--
CREATE DATABASE IF NOT EXISTS `pytes` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `pytes`;

-- --------------------------------------------------------

--
-- Structură tabel pentru tabel `pwr_data`
--

CREATE TABLE `pwr_data` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `record_time` datetime NOT NULL DEFAULT current_timestamp(),
  `power` int(11) NOT NULL,
  `voltage` float NOT NULL,
  `current` float NOT NULL,
  `temperature` decimal(11,0) NOT NULL,
  `soc` int(11) NOT NULL,
  `basic_st` varchar(11) NOT NULL,
  `volt_st` varchar(11) NOT NULL,
  `current_st` varchar(11) NOT NULL,
  `temp_st` varchar(11) NOT NULL,
  `coul_st` varchar(11) NOT NULL,
  `soh_st` varchar(11) NOT NULL,
  `heater_st` varchar(11) NOT NULL,
  `bat_events` int(11) NOT NULL,
  `power_events` int(11) NOT NULL,
  `sys_events` int(11) NOT NULL,
   CONSTRAINT id PRIMARY KEY (id)
  

) ENGINE=InnoDB DEFAULT CHARSET=utf8;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
