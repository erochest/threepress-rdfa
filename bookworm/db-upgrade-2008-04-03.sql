-- Evolve application library
ALTER TABLE `library_userarchive` ADD COLUMN `owner` bool ;
UPDATE `library_userarchive` SET `owner` = True WHERE `owner` IS NULL;
ALTER TABLE `library_userarchive` MODIFY COLUMN `owner` bool NOT NULL;
