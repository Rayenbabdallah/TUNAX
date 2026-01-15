CREATE TABLE `users` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `email` varchar(120) UNIQUE NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` varchar(50) NOT NULL COMMENT 'CITIZEN, BUSINESS, AGENT, INSPECTOR, FINANCE, CONTENTIEUX, URBANISM, MUNICIPAL_ADMIN, MINISTRY',
  `first_name` varchar(100),
  `last_name` varchar(100),
  `cin` varchar(20) UNIQUE COMMENT 'National ID',
  `phone` varchar(20),
  `address` text,
  `commune_id` int COMMENT 'Work commune for officials',
  `is_active` boolean DEFAULT true,
  `is_verified` boolean DEFAULT false,
  `created_at` timestamp DEFAULT (now()),
  `updated_at` timestamp DEFAULT (now())
);

CREATE TABLE `communes` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `name_ar` varchar(100) COMMENT 'Arabic name',
  `postal_code` varchar(10),
  `region` varchar(100),
  `delegation` varchar(100),
  `total_population` int,
  `total_properties` int,
  `total_lands` int,
  `created_at` timestamp DEFAULT (now())
);

CREATE TABLE `two_factor_auth` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `user_id` int UNIQUE NOT NULL,
  `secret_key` varchar(255) NOT NULL,
  `is_enabled` boolean DEFAULT false,
  `backup_codes` text COMMENT 'JSON array of backup codes',
  `created_at` timestamp DEFAULT (now()),
  `last_used_at` timestamp
);

CREATE TABLE `properties` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `owner_id` int NOT NULL,
  `commune_id` int NOT NULL,
  `address` text NOT NULL,
  `postal_code` varchar(10),
  `governorate` varchar(100),
  `delegation` varchar(100),
  `locality` varchar(100),
  `ilot` varchar(50),
  `street` varchar(200),
  `title_deed_number` varchar(100) UNIQUE,
  `cadastral_reference` varchar(100),
  `property_type` varchar(50) COMMENT 'RESIDENTIAL, COMMERCIAL, INDUSTRIAL, MIXED',
  `total_surface_m2` decimal(10,2) NOT NULL,
  `covered_surface_m2` decimal(10,2) NOT NULL,
  `is_main_residence` boolean DEFAULT false,
  `construction_year` int,
  `num_floors` int,
  `affectation` varchar(100) COMMENT 'Usage: Housing, Office, Shop, etc.',
  `tib_category` int COMMENT '1(≤100m²), 2(101-200m²), 3(201-400m²), 4(>400m²)',
  `reference_price_per_m2` decimal(10,2) COMMENT 'Set by municipality within legal bounds',
  `status` varchar(50) DEFAULT 'PENDING' COMMENT 'PENDING, VERIFIED, REJECTED',
  `verified_by` int,
  `verified_at` timestamp,
  `rejection_reason` text,
  `available_services_count` int DEFAULT 0 COMMENT 'Auto-calculated from MunicipalConfig',
  `created_at` timestamp DEFAULT (now()),
  `updated_at` timestamp DEFAULT (now())
);

CREATE TABLE `lands` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `owner_id` int NOT NULL,
  `commune_id` int NOT NULL,
  `address` text,
  `governorate` varchar(100),
  `delegation` varchar(100),
  `locality` varchar(100),
  `title_deed_number` varchar(100) UNIQUE,
  `cadastral_reference` varchar(100),
  `urban_zone` varchar(100) COMMENT 'Urban planning zone classification',
  `surface_m2` decimal(10,2) NOT NULL,
  `land_type` varchar(50) COMMENT 'AGRICULTURAL, CONSTRUCTIBLE, URBAN, INDUSTRIAL',
  `ttnb_rate` decimal(5,4) COMMENT 'Tax rate per m² based on zone',
  `status` varchar(50) DEFAULT 'PENDING',
  `verified_by` int,
  `verified_at` timestamp,
  `rejection_reason` text,
  `created_at` timestamp DEFAULT (now()),
  `updated_at` timestamp DEFAULT (now())
);

CREATE TABLE `taxes` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `property_id` int,
  `land_id` int,
  `commune_id` int NOT NULL,
  `taxpayer_id` int NOT NULL COMMENT 'Owner at time of tax generation',
  `tax_year` int NOT NULL,
  `tax_type` varchar(10) NOT NULL COMMENT 'TIB or TTNB',
  `base_amount` decimal(10,2) NOT NULL COMMENT 'Base tax before exemptions',
  `exemption_amount` decimal(10,2) DEFAULT 0,
  `final_amount` decimal(10,2) NOT NULL COMMENT 'After exemptions, before penalties',
  `paid_amount` decimal(10,2) DEFAULT 0,
  `remaining_amount` decimal(10,2) NOT NULL,
  `status` varchar(50) DEFAULT 'PENDING' COMMENT 'PENDING, PAID, PARTIAL, OVERDUE, DISPUTED',
  `due_date` date NOT NULL,
  `paid_at` timestamp,
  `created_at` timestamp DEFAULT (now()),
  `updated_at` timestamp DEFAULT (now())
);

CREATE TABLE `penalties` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `tax_id` int NOT NULL,
  `penalty_type` varchar(50) COMMENT 'LATE_PAYMENT, NON_DECLARATION',
  `penalty_rate` decimal(5,4) COMMENT '1.25% per month',
  `months_late` int,
  `penalty_amount` decimal(10,2) NOT NULL COMMENT 'Auto-calculated, capped at 50% of base',
  `calculated_at` timestamp DEFAULT (now())
);

CREATE TABLE `exemptions` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `property_id` int,
  `land_id` int,
  `exemption_type` varchar(50) NOT NULL COMMENT 'MAIN_RESIDENCE, DISABILITY, SENIOR_CITIZEN, LOW_INCOME, SOCIAL_HOUSING',
  `percentage` decimal(5,2) NOT NULL COMMENT '0-100%',
  `justification` text,
  `supporting_doc_path` varchar(500),
  `status` varchar(50) DEFAULT 'PENDING' COMMENT 'PENDING, APPROVED, REJECTED',
  `approved_by` int,
  `approved_at` timestamp,
  `rejection_reason` text,
  `valid_from` date NOT NULL,
  `valid_until` date,
  `created_at` timestamp DEFAULT (now())
);

CREATE TABLE `payments` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `tax_id` int NOT NULL,
  `payer_id` int NOT NULL,
  `payment_plan_id` int COMMENT 'If part of installment plan',
  `amount` decimal(10,2) NOT NULL,
  `payment_method` varchar(50) NOT NULL COMMENT 'CASH, CHECK, CARD, BANK_TRANSFER, MOBILE_PAYMENT',
  `transaction_reference` varchar(100) UNIQUE,
  `payment_date` timestamp DEFAULT (now()),
  `receipt_number` varchar(100) UNIQUE,
  `receipt_path` varchar(500),
  `processed_by` int COMMENT 'Finance officer',
  `status` varchar(50) DEFAULT 'COMPLETED' COMMENT 'PENDING, COMPLETED, FAILED, REFUNDED',
  `notes` text,
  `created_at` timestamp DEFAULT (now())
);

CREATE TABLE `payment_plans` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `tax_id` int UNIQUE NOT NULL,
  `taxpayer_id` int NOT NULL,
  `total_amount` decimal(10,2) NOT NULL,
  `num_installments` int NOT NULL COMMENT 'Max 12 months',
  `installment_amount` decimal(10,2) NOT NULL,
  `status` varchar(50) DEFAULT 'ACTIVE' COMMENT 'ACTIVE, COMPLETED, DEFAULTED',
  `start_date` date NOT NULL,
  `next_payment_date` date,
  `approved_by` int,
  `approved_at` timestamp,
  `created_at` timestamp DEFAULT (now())
);

CREATE TABLE `inspections` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `property_id` int,
  `land_id` int,
  `inspector_id` int NOT NULL,
  `inspection_type` varchar(50) COMMENT 'DECLARATION_VERIFICATION, SATELLITE_COMPARISON, FIELD_VISIT',
  `inspection_date` timestamp NOT NULL,
  `satellite_verified` boolean DEFAULT false,
  `discrepancy_found` boolean DEFAULT false,
  `discrepancy_details` text,
  `measured_surface_m2` decimal(10,2),
  `declared_surface_m2` decimal(10,2),
  `difference_percentage` decimal(5,2),
  `recommendation` varchar(50) COMMENT 'APPROVE, REJECT, REQUIRE_CORRECTION, FURTHER_INVESTIGATION',
  `inspector_notes` text,
  `status` varchar(50) DEFAULT 'COMPLETED',
  `follow_up_required` boolean DEFAULT false,
  `created_at` timestamp DEFAULT (now())
);

CREATE TABLE `satellite_verifications` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `inspection_id` int NOT NULL,
  `satellite_image_url` varchar(500),
  `image_capture_date` date,
  `ai_detected_surface_m2` decimal(10,2),
  `confidence_score` decimal(3,2) COMMENT '0.00 to 1.00',
  `matches_declaration` boolean,
  `variance_m2` decimal(10,2),
  `variance_percentage` decimal(5,2),
  `verified_at` timestamp DEFAULT (now())
);

CREATE TABLE `disputes` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `tax_id` int NOT NULL,
  `claimant_id` int NOT NULL COMMENT 'Taxpayer filing dispute',
  `dispute_type` varchar(50) COMMENT 'AMOUNT_CONTESTED, EXEMPTION_DENIED, PENALTY_CONTESTED, CALCULATION_ERROR',
  `claimed_amount` decimal(10,2),
  `reason` text NOT NULL,
  `supporting_documents` text COMMENT 'JSON array of doc paths',
  `status` varchar(50) DEFAULT 'PENDING' COMMENT 'PENDING, UNDER_REVIEW, RESOLVED, REJECTED',
  `assigned_to` int COMMENT 'Contentieux officer',
  `resolution` text,
  `resolved_amount` decimal(10,2),
  `resolved_by` int,
  `resolved_at` timestamp,
  `created_at` timestamp DEFAULT (now()),
  `updated_at` timestamp DEFAULT (now())
);

CREATE TABLE `reclamations` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `property_id` int,
  `land_id` int,
  `tax_id` int,
  `claimant_id` int NOT NULL,
  `reclamation_type` varchar(50) COMMENT 'TAX_CORRECTION, SURFACE_CORRECTION, OWNERSHIP_DISPUTE, DATA_ERROR',
  `description` text NOT NULL,
  `status` varchar(50) DEFAULT 'SUBMITTED' COMMENT 'SUBMITTED, UNDER_REVIEW, APPROVED, REJECTED',
  `assigned_to` int,
  `admin_response` text,
  `resolved_by` int,
  `resolved_at` timestamp,
  `created_at` timestamp DEFAULT (now())
);

CREATE TABLE `permits` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `applicant_id` int NOT NULL,
  `property_id` int,
  `permit_type` varchar(50) NOT NULL COMMENT 'CONSTRUCTION, RENOVATION, DEMOLITION, EXTENSION',
  `project_description` text NOT NULL,
  `estimated_cost` decimal(12,2),
  `planned_surface_m2` decimal(10,2),
  `architectural_plans_path` varchar(500),
  `supporting_docs` text COMMENT 'JSON array',
  `status` varchar(50) DEFAULT 'SUBMITTED' COMMENT 'SUBMITTED, UNDER_REVIEW, APPROVED, REJECTED, EXPIRED',
  `reviewed_by` int COMMENT 'Urbanism officer',
  `approval_date` timestamp,
  `expiry_date` timestamp,
  `permit_number` varchar(100) UNIQUE,
  `rejection_reason` text,
  `created_at` timestamp DEFAULT (now()),
  `updated_at` timestamp DEFAULT (now())
);

CREATE TABLE `documents` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `entity_type` varchar(50) COMMENT 'PROPERTY, LAND, TAX, PERMIT, INSPECTION, DISPUTE',
  `entity_id` int COMMENT 'ID of parent entity',
  `uploader_id` int NOT NULL,
  `document_type` varchar(50) COMMENT 'TITLE_DEED, TAX_RECEIPT, CADASTRAL_PLAN, ID_DOCUMENT, SITE_PHOTO, etc.',
  `file_name` varchar(255) NOT NULL,
  `file_path` varchar(500) NOT NULL,
  `file_size_kb` int,
  `mime_type` varchar(100),
  `description` text,
  `uploaded_at` timestamp DEFAULT (now())
);

CREATE TABLE `declarations` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `declarant_id` int NOT NULL,
  `declaration_type` varchar(50) COMMENT 'PROPERTY_DECLARATION, LAND_DECLARATION, TAX_DECLARATION',
  `property_id` int,
  `land_id` int,
  `status` varchar(50) DEFAULT 'SUBMITTED' COMMENT 'SUBMITTED, VERIFIED, REJECTED',
  `verified_by` int,
  `verified_at` timestamp,
  `notes` text,
  `created_at` timestamp DEFAULT (now())
);

CREATE TABLE `municipal_configs` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `commune_id` int UNIQUE NOT NULL,
  `service_water` boolean DEFAULT false,
  `service_electricity` boolean DEFAULT false,
  `service_sewage` boolean DEFAULT false,
  `service_garbage` boolean DEFAULT false,
  `service_street_lighting` boolean DEFAULT false,
  `service_road_maintenance` boolean DEFAULT false,
  `service_public_transport` boolean DEFAULT false,
  `total_services_count` int DEFAULT 0,
  `tib_service_rate` decimal(5,4) COMMENT 'Auto-calculated based on service count',
  `ref_price_cat1` decimal(10,2) COMMENT 'Category 1: ≤100 m² (100-178 TND/m²)',
  `ref_price_cat2` decimal(10,2) COMMENT 'Category 2: 101-200 m² (163-238 TND/m²)',
  `ref_price_cat3` decimal(10,2) COMMENT 'Category 3: 201-400 m² (217-297 TND/m²)',
  `ref_price_cat4` decimal(10,2) COMMENT 'Category 4: >400 m² (271-356 TND/m²)',
  `updated_at` timestamp DEFAULT (now()),
  `updated_by` int
);

CREATE TABLE `budgets` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `commune_id` int NOT NULL,
  `fiscal_year` int NOT NULL,
  `total_budget` decimal(15,2) NOT NULL,
  `infrastructure_budget` decimal(15,2),
  `services_budget` decimal(15,2),
  `administration_budget` decimal(15,2),
  `projected_tib_revenue` decimal(15,2),
  `projected_ttnb_revenue` decimal(15,2),
  `actual_tib_revenue` decimal(15,2) DEFAULT 0,
  `actual_ttnb_revenue` decimal(15,2) DEFAULT 0,
  `total_votes` int DEFAULT 0,
  `approved_votes` int DEFAULT 0,
  `rejected_votes` int DEFAULT 0,
  `status` varchar(50) DEFAULT 'DRAFT' COMMENT 'DRAFT, VOTING, APPROVED, REJECTED',
  `created_at` timestamp DEFAULT (now()),
  `updated_at` timestamp DEFAULT (now())
);

CREATE TABLE `notifications` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `notification_type` varchar(50) COMMENT 'TAX_DUE, PAYMENT_RECEIVED, PERMIT_APPROVED, DISPUTE_RESOLVED',
  `title` varchar(255) NOT NULL,
  `message` text NOT NULL,
  `related_entity_type` varchar(50) COMMENT 'TAX, PAYMENT, PERMIT, DISPUTE',
  `related_entity_id` int,
  `is_read` boolean DEFAULT false,
  `read_at` timestamp,
  `created_at` timestamp DEFAULT (now())
);

CREATE TABLE `audit_logs` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `user_id` int COMMENT 'System actions may have no user',
  `action` varchar(100) NOT NULL COMMENT 'CREATE, UPDATE, DELETE, LOGIN, APPROVE, REJECT',
  `entity_type` varchar(50) COMMENT 'USER, PROPERTY, TAX, PAYMENT, etc.',
  `entity_id` int,
  `old_values` text COMMENT 'JSON snapshot before change',
  `new_values` text COMMENT 'JSON snapshot after change',
  `ip_address` varchar(45),
  `user_agent` text,
  `created_at` timestamp DEFAULT (now())
);

CREATE INDEX `users_index_0` ON `users` (`email`);

CREATE INDEX `users_index_1` ON `users` (`cin`);

CREATE INDEX `users_index_2` ON `users` (`role`);

CREATE INDEX `users_index_3` ON `users` (`commune_id`);

CREATE INDEX `communes_index_4` ON `communes` (`postal_code`);

CREATE INDEX `communes_index_5` ON `communes` (`region`);

CREATE INDEX `properties_index_6` ON `properties` (`owner_id`);

CREATE INDEX `properties_index_7` ON `properties` (`commune_id`);

CREATE INDEX `properties_index_8` ON `properties` (`title_deed_number`);

CREATE INDEX `properties_index_9` ON `properties` (`cadastral_reference`);

CREATE INDEX `properties_index_10` ON `properties` (`status`);

CREATE INDEX `lands_index_11` ON `lands` (`owner_id`);

CREATE INDEX `lands_index_12` ON `lands` (`commune_id`);

CREATE INDEX `lands_index_13` ON `lands` (`title_deed_number`);

CREATE INDEX `lands_index_14` ON `lands` (`status`);

CREATE INDEX `taxes_index_15` ON `taxes` (`property_id`);

CREATE INDEX `taxes_index_16` ON `taxes` (`land_id`);

CREATE INDEX `taxes_index_17` ON `taxes` (`commune_id`);

CREATE INDEX `taxes_index_18` ON `taxes` (`taxpayer_id`);

CREATE INDEX `taxes_index_19` ON `taxes` (`tax_year`);

CREATE INDEX `taxes_index_20` ON `taxes` (`tax_type`);

CREATE INDEX `taxes_index_21` ON `taxes` (`status`);

CREATE INDEX `taxes_index_22` ON `taxes` (`due_date`);

CREATE INDEX `penalties_index_23` ON `penalties` (`tax_id`);

CREATE INDEX `exemptions_index_24` ON `exemptions` (`property_id`);

CREATE INDEX `exemptions_index_25` ON `exemptions` (`land_id`);

CREATE INDEX `exemptions_index_26` ON `exemptions` (`status`);

CREATE INDEX `exemptions_index_27` ON `exemptions` (`valid_from`);

CREATE INDEX `exemptions_index_28` ON `exemptions` (`valid_until`);

CREATE INDEX `payments_index_29` ON `payments` (`tax_id`);

CREATE INDEX `payments_index_30` ON `payments` (`payer_id`);

CREATE INDEX `payments_index_31` ON `payments` (`payment_plan_id`);

CREATE INDEX `payments_index_32` ON `payments` (`transaction_reference`);

CREATE INDEX `payments_index_33` ON `payments` (`receipt_number`);

CREATE INDEX `payments_index_34` ON `payments` (`payment_date`);

CREATE INDEX `payment_plans_index_35` ON `payment_plans` (`tax_id`);

CREATE INDEX `payment_plans_index_36` ON `payment_plans` (`taxpayer_id`);

CREATE INDEX `payment_plans_index_37` ON `payment_plans` (`status`);

CREATE INDEX `inspections_index_38` ON `inspections` (`property_id`);

CREATE INDEX `inspections_index_39` ON `inspections` (`land_id`);

CREATE INDEX `inspections_index_40` ON `inspections` (`inspector_id`);

CREATE INDEX `inspections_index_41` ON `inspections` (`inspection_date`);

CREATE INDEX `satellite_verifications_index_42` ON `satellite_verifications` (`inspection_id`);

CREATE INDEX `disputes_index_43` ON `disputes` (`tax_id`);

CREATE INDEX `disputes_index_44` ON `disputes` (`claimant_id`);

CREATE INDEX `disputes_index_45` ON `disputes` (`status`);

CREATE INDEX `disputes_index_46` ON `disputes` (`assigned_to`);

CREATE INDEX `reclamations_index_47` ON `reclamations` (`property_id`);

CREATE INDEX `reclamations_index_48` ON `reclamations` (`land_id`);

CREATE INDEX `reclamations_index_49` ON `reclamations` (`tax_id`);

CREATE INDEX `reclamations_index_50` ON `reclamations` (`claimant_id`);

CREATE INDEX `reclamations_index_51` ON `reclamations` (`status`);

CREATE INDEX `permits_index_52` ON `permits` (`applicant_id`);

CREATE INDEX `permits_index_53` ON `permits` (`property_id`);

CREATE INDEX `permits_index_54` ON `permits` (`status`);

CREATE INDEX `permits_index_55` ON `permits` (`permit_number`);

CREATE INDEX `documents_index_56` ON `documents` (`entity_type`);

CREATE INDEX `documents_index_57` ON `documents` (`entity_id`);

CREATE INDEX `documents_index_58` ON `documents` (`uploader_id`);

CREATE INDEX `documents_index_59` ON `documents` (`document_type`);

CREATE INDEX `declarations_index_60` ON `declarations` (`declarant_id`);

CREATE INDEX `declarations_index_61` ON `declarations` (`property_id`);

CREATE INDEX `declarations_index_62` ON `declarations` (`land_id`);

CREATE INDEX `declarations_index_63` ON `declarations` (`status`);

CREATE INDEX `municipal_configs_index_64` ON `municipal_configs` (`commune_id`);

CREATE INDEX `budgets_index_65` ON `budgets` (`commune_id`);

CREATE INDEX `budgets_index_66` ON `budgets` (`fiscal_year`);

CREATE INDEX `budgets_index_67` ON `budgets` (`status`);

CREATE INDEX `notifications_index_68` ON `notifications` (`user_id`);

CREATE INDEX `notifications_index_69` ON `notifications` (`is_read`);

CREATE INDEX `notifications_index_70` ON `notifications` (`created_at`);

CREATE INDEX `audit_logs_index_71` ON `audit_logs` (`user_id`);

CREATE INDEX `audit_logs_index_72` ON `audit_logs` (`action`);

CREATE INDEX `audit_logs_index_73` ON `audit_logs` (`entity_type`);

CREATE INDEX `audit_logs_index_74` ON `audit_logs` (`entity_id`);

CREATE INDEX `audit_logs_index_75` ON `audit_logs` (`created_at`);

ALTER TABLE `users` ADD FOREIGN KEY (`commune_id`) REFERENCES `communes` (`id`);

ALTER TABLE `two_factor_auth` ADD FOREIGN KEY (`user_id`) REFERENCES `users` (`id`);

ALTER TABLE `properties` ADD FOREIGN KEY (`owner_id`) REFERENCES `users` (`id`);

ALTER TABLE `properties` ADD FOREIGN KEY (`commune_id`) REFERENCES `communes` (`id`);

ALTER TABLE `properties` ADD FOREIGN KEY (`verified_by`) REFERENCES `users` (`id`);

ALTER TABLE `lands` ADD FOREIGN KEY (`owner_id`) REFERENCES `users` (`id`);

ALTER TABLE `lands` ADD FOREIGN KEY (`commune_id`) REFERENCES `communes` (`id`);

ALTER TABLE `lands` ADD FOREIGN KEY (`verified_by`) REFERENCES `users` (`id`);

ALTER TABLE `taxes` ADD FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`);

ALTER TABLE `taxes` ADD FOREIGN KEY (`land_id`) REFERENCES `lands` (`id`);

ALTER TABLE `taxes` ADD FOREIGN KEY (`commune_id`) REFERENCES `communes` (`id`);

ALTER TABLE `taxes` ADD FOREIGN KEY (`taxpayer_id`) REFERENCES `users` (`id`);

ALTER TABLE `penalties` ADD FOREIGN KEY (`tax_id`) REFERENCES `taxes` (`id`);

ALTER TABLE `exemptions` ADD FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`);

ALTER TABLE `exemptions` ADD FOREIGN KEY (`land_id`) REFERENCES `lands` (`id`);

ALTER TABLE `exemptions` ADD FOREIGN KEY (`approved_by`) REFERENCES `users` (`id`);

ALTER TABLE `payments` ADD FOREIGN KEY (`tax_id`) REFERENCES `taxes` (`id`);

ALTER TABLE `payments` ADD FOREIGN KEY (`payer_id`) REFERENCES `users` (`id`);

ALTER TABLE `payments` ADD FOREIGN KEY (`payment_plan_id`) REFERENCES `payment_plans` (`id`);

ALTER TABLE `payments` ADD FOREIGN KEY (`processed_by`) REFERENCES `users` (`id`);

ALTER TABLE `payment_plans` ADD FOREIGN KEY (`tax_id`) REFERENCES `taxes` (`id`);

ALTER TABLE `payment_plans` ADD FOREIGN KEY (`taxpayer_id`) REFERENCES `users` (`id`);

ALTER TABLE `payment_plans` ADD FOREIGN KEY (`approved_by`) REFERENCES `users` (`id`);

ALTER TABLE `inspections` ADD FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`);

ALTER TABLE `inspections` ADD FOREIGN KEY (`land_id`) REFERENCES `lands` (`id`);

ALTER TABLE `inspections` ADD FOREIGN KEY (`inspector_id`) REFERENCES `users` (`id`);

ALTER TABLE `satellite_verifications` ADD FOREIGN KEY (`inspection_id`) REFERENCES `inspections` (`id`);

ALTER TABLE `disputes` ADD FOREIGN KEY (`tax_id`) REFERENCES `taxes` (`id`);

ALTER TABLE `disputes` ADD FOREIGN KEY (`claimant_id`) REFERENCES `users` (`id`);

ALTER TABLE `disputes` ADD FOREIGN KEY (`assigned_to`) REFERENCES `users` (`id`);

ALTER TABLE `disputes` ADD FOREIGN KEY (`resolved_by`) REFERENCES `users` (`id`);

ALTER TABLE `reclamations` ADD FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`);

ALTER TABLE `reclamations` ADD FOREIGN KEY (`land_id`) REFERENCES `lands` (`id`);

ALTER TABLE `reclamations` ADD FOREIGN KEY (`tax_id`) REFERENCES `taxes` (`id`);

ALTER TABLE `reclamations` ADD FOREIGN KEY (`claimant_id`) REFERENCES `users` (`id`);

ALTER TABLE `reclamations` ADD FOREIGN KEY (`assigned_to`) REFERENCES `users` (`id`);

ALTER TABLE `reclamations` ADD FOREIGN KEY (`resolved_by`) REFERENCES `users` (`id`);

ALTER TABLE `permits` ADD FOREIGN KEY (`applicant_id`) REFERENCES `users` (`id`);

ALTER TABLE `permits` ADD FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`);

ALTER TABLE `permits` ADD FOREIGN KEY (`reviewed_by`) REFERENCES `users` (`id`);

ALTER TABLE `documents` ADD FOREIGN KEY (`uploader_id`) REFERENCES `users` (`id`);

ALTER TABLE `declarations` ADD FOREIGN KEY (`declarant_id`) REFERENCES `users` (`id`);

ALTER TABLE `declarations` ADD FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`);

ALTER TABLE `declarations` ADD FOREIGN KEY (`land_id`) REFERENCES `lands` (`id`);

ALTER TABLE `declarations` ADD FOREIGN KEY (`verified_by`) REFERENCES `users` (`id`);

ALTER TABLE `municipal_configs` ADD FOREIGN KEY (`commune_id`) REFERENCES `communes` (`id`);

ALTER TABLE `municipal_configs` ADD FOREIGN KEY (`updated_by`) REFERENCES `users` (`id`);

ALTER TABLE `budgets` ADD FOREIGN KEY (`commune_id`) REFERENCES `communes` (`id`);

ALTER TABLE `notifications` ADD FOREIGN KEY (`user_id`) REFERENCES `users` (`id`);

ALTER TABLE `audit_logs` ADD FOREIGN KEY (`user_id`) REFERENCES `users` (`id`);
