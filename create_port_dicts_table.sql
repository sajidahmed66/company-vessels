-- Create port_dicts table for MagicPort port data
CREATE TABLE IF NOT EXISTS port_dicts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    port_name VARCHAR(255) NOT NULL,
    country VARCHAR(100) NOT NULL,
    unlocode VARCHAR(10),
    url TEXT NOT NULL,
    is_active TINYINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Indexes for better performance
    INDEX idx_port_name (port_name),
    INDEX idx_country (country),
    INDEX idx_unlocode (unlocode),
    INDEX idx_is_active (is_active),
    INDEX idx_created_at (created_at),

    -- Unique constraint to avoid duplicates
    UNIQUE KEY unique_port_url (port_name, country, url(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;