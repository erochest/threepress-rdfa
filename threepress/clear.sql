BEGIN;
DROP TABLE `search_page`;
ALTER TABLE `search_part` DROP FOREIGN KEY document_id_refs_id_5e82997;
ALTER TABLE `search_chapter` DROP FOREIGN KEY document_id_refs_id_5a244efa;
DROP TABLE `search_document`;
ALTER TABLE `search_chapter` DROP FOREIGN KEY part_id_refs_id_6fba3a7e;
DROP TABLE `search_part`;
DROP TABLE `search_chapter`;
COMMIT;
