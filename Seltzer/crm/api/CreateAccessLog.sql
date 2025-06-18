-- this script is used to create the ACCESSLOG table.
-- it keeps track of every RFID key swipe at the door
-- for future reference to know who came to the space
-- and if the door let them in or not.
-- SERIAL = the RFID serial number read by the reader
-- ACCESS = 0 if not allowed 1 if access granted
-- REASON = door lock returns "key not found" or "balance owed = $$"
-- This table is written to by the door lock as keys are swiped.
-- Josh Pritt June 9, 2025
CREATE TABLE accesslog (
    ID INT PRIMARY KEY AUTO_INCREMENT,
    SERIAL VARCHAR(20) NOT NULL,
    ACCESS TINYINT(1) NOT NULL, -- MySQL uses TINYINT(1) for boolean-like values
    REASON VARCHAR(255),
    SWIPETIME TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
);