-- ============================================================
--  MySQL Source Database Schema
--  Database: demand_db
--  Purpose:  Source OLTP tables for the demand approval workflow
-- ============================================================

CREATE DATABASE IF NOT EXISTS demand_db;
USE demand_db;

-- ── Committee Members ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS committee (
    member_id   INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    member_name VARCHAR(100) NOT NULL,
    role        ENUM('chairman', 'vice_chairman', 'member') NOT NULL,
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP
);

-- ── Demands ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS demands (
    demand_id           INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
    demand_number       VARCHAR(20)  NOT NULL UNIQUE,
    initialization_date DATE         NOT NULL,
    end_date            DATE,
    created_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP
);

-- ── Comments (committee queries to the demanding officer) ────
CREATE TABLE IF NOT EXISTS comments (
    comment_id     INT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    demand_id      INT       NOT NULL,
    member_id      INT       NOT NULL,
    requested_date DATE      NOT NULL,   -- query raised date
    response_date  DATE,                 -- user response date
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                   ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (demand_id)  REFERENCES demands(demand_id),
    FOREIGN KEY (member_id)  REFERENCES committee(member_id)
);

-- ── Recommendations ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS recommendation (
    recommendation_id INT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    demand_id         INT       NOT NULL,
    member_id         INT       NOT NULL,
    rec_date          DATE      NOT NULL,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                      ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (demand_id)  REFERENCES demands(demand_id),
    FOREIGN KEY (member_id)  REFERENCES committee(member_id)
);

-- ── Seed committee members ───────────────────────────────────
INSERT IGNORE INTO committee (member_id, member_name, role) VALUES
(1, 'Chairman',          'chairman'),
(2, 'Vice Chairman',     'vice_chairman'),
(3, 'Material Mgmt Rep', 'member'),
(4, 'Finance Rep',       'member'),
(5, 'Technical Rep',     'member');
