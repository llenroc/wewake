CREATE TABLE admins (groupid text, phone text);
CREATE TABLE alarms (groupid text, alarm text, tries integer);
CREATE TABLE buzzer (phone text, groupid text, tries integer);
CREATE TABLE groups (groupid text, phone text, avail text);
CREATE TABLE inflight (phone text, groupid text);
CREATE TABLE users (phone text, name text);