-- Vessel Validation Tracking Table
-- This table tracks which vessels have been validated and their validation status

CREATE TABLE vessel_validation_tracking (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    vessel_id BIGINT UNSIGNED NOT NULL,
    validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('success', 'error', 'needs_review') NOT NULL,
    company_id_corrected BOOLEAN DEFAULT FALSE,
    manager_company_id_corrected BOOLEAN DEFAULT FALSE,
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY unique_vessel (vessel_id),
    FOREIGN KEY (vessel_id) REFERENCES vessels(id) ON DELETE CASCADE,
    INDEX idx_status (status),
    INDEX idx_validated_at (validated_at)
) COLLATE = utf8mb4_unicode_ci;

-- Query to check unprocessed vessels count
-- SELECT COUNT(*) as unprocessed_count
-- FROM vessels v
-- LEFT JOIN vessel_validation_tracking vvt ON v.id = vvt.vessel_id
-- WHERE vvt.vessel_id IS NULL;

-- Query to see validation summary
-- SELECT
--     status,
--     COUNT(*) as count,
--     SUM(company_id_corrected) as company_corrections,
--     SUM(manager_company_id_corrected) as manager_corrections
-- FROM vessel_validation_tracking
-- GROUP BY status;
