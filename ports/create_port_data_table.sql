-- Create port_data table for storing scraped port information
CREATE TABLE IF NOT EXISTS `port_data` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) DEFAULT NULL,
  `country` varchar(100) DEFAULT NULL,
  `unlocode` varchar(10) DEFAULT NULL,
  `latitude` decimal(10,8) DEFAULT NULL,
  `longitude` decimal(11,8) DEFAULT NULL,
  `navigation` json DEFAULT NULL,
  `depths` json DEFAULT NULL,
  `port_characteristics` json DEFAULT NULL,
  `restrictions` json DEFAULT NULL,
  `port_equipment` json DEFAULT NULL,
  `communication` json DEFAULT NULL,
  `scraped_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `source_url` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unlocode` (`unlocode`),
  KEY `country` (`country`),
  KEY `scraped_at` (`scraped_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;