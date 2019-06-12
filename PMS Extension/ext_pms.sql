-- phpMyAdmin SQL Dump
-- version 4.6.5.2
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Apr 10, 2017 at 06:34 AM
-- Server version: 5.5.54-0ubuntu0.14.04.1
-- PHP Version: 5.6.30

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `ext_pms`
--

-- --------------------------------------------------------

--
-- Table structure for table `all_faculty_details`
--

CREATE TABLE `all_faculty_details` (
  `fid` int(4) NOT NULL,
  `institute` varchar(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(70) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `designation` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `gscholar_id` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Google Scholar Code'
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `all_faculty_details`
--

INSERT INTO `all_faculty_details` (`fid`, `institute`, `name`, `designation`, `gscholar_id`) VALUES
(157, 'IITH', 'Bheemarjuna Reddy Tamma', 'Head & Associate Professor', 'FYHCD2kAAAAJ'),
(158, 'IITH', 'Antony Franklin', 'Assistant Professor', '6Jxd9Z8AAAAJ'),
(159, 'IITH', 'C. Krishna Mohan', 'Associate Professor', 'GvSsuVEAAAAJ'),
(160, 'IITH', 'Kotaro Kataoka', 'Assistant Professor', 'uAuKJY4AAAAJ'),
(161, 'IITH', 'Manish Singh', 'Assistant Professor', 'I1jX5vgAAAAJ'),
(162, 'IITH', 'Manohar Kaul', 'Assistant Professor', 'jNroyK4AAAAJ'),
(163, 'IITH', 'Maunendra Sankar Desarkar', 'Assistant Professor', 'W8LJ-tEAAAAJ'),
(164, 'IITH', 'M. V. Panduranga Rao', 'AssociateProfessor', ''),
(165, 'IITH', 'N. R. Aravind', 'Assistant Professor', ''),
(166, 'IITH', 'Ramakrishna Upadrasta', 'Assistant Professor', '3qZCtWYAAAAJ'),
(167, 'IITH', 'Sathya Peri', 'AssociateProfessor', 'fUUk1jkAAAAJ'),
(168, 'IITH', 'Saurabh Joshi', 'Assistant Professor', 'MvHEGbYAAAAJ'),
(169, 'IITH', 'Sobhan Babu', 'AssociateProfessor', 'UFMtsfkAAAAJ'),
(170, 'IITH', 'Sparsh Mittal', 'Assistant Professor', 'Hz44YrEAAAAJ'),
(171, 'IITH', 'Srijith P. K.', 'Assistant Professor', 'C1YpEWsAAAAJ'),
(172, 'IITH', 'Subrahmanyam Kalyanasundaram', 'Assistant Professor', ''),
(173, 'IITH', 'Vineeth N Balasubramanian', 'Assistant Professor', '7soDcboAAAAJ');

-- --------------------------------------------------------

--
-- Table structure for table `publication_count`
--

CREATE TABLE `publication_count` (
  `fid` int(4) UNSIGNED NOT NULL,
  `year` varchar(4) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `pub_count` int(4) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Dumping data for table `publication_count`
--

INSERT INTO `publication_count` (`fid`, `year`, `pub_count`) VALUES
(157, '2003', 1),
(157, '2004', 2),
(157, '2005', 2),
(157, '2006', 5),
(157, '2007', 3),
(157, '2008', 3),
(157, '2009', 3),
(157, '2010', 9),
(157, '2011', 4),
(157, '2012', 3),
(157, '2013', 6),
(157, '2014', 10),
(157, '2015', 11),
(157, '2016', 9),
(158, '2007', 3),
(158, '2008', 7),
(158, '2009', 4),
(158, '2010', 5),
(158, '2011', 1),
(158, '2012', 2),
(158, '2013', 3),
(158, '2014', 3),
(158, '2015', 8),
(158, '2016', 7),
(159, '2004', 1),
(159, '2005', 1),
(159, '2007', 1),
(159, '2008', 1),
(159, '2010', 2),
(159, '2011', 2),
(159, '2013', 1),
(159, '2014', 10),
(159, '2015', 12),
(159, '2016', 9),
(159, '2017', 3);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `all_faculty_details`
--
ALTER TABLE `all_faculty_details`
  ADD PRIMARY KEY (`fid`);

--
-- Indexes for table `publication_count`
--
ALTER TABLE `publication_count`
  ADD PRIMARY KEY (`fid`,`year`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `all_faculty_details`
--
ALTER TABLE `all_faculty_details`
  MODIFY `fid` int(4) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=174;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
