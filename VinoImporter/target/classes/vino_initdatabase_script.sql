INSERT INTO provider(id, "name")VALUES ((SELECT nextval('provider_id_seq'), "Wermuth SA.");
INSERT INTO provider(id, "name")VALUES ((SELECT nextval('provider_id_seq'), "Steinfels");
INSERT INTO provider(id, "name")VALUES ((SELECT nextval('provider_id_seq'), "Weinbörse");
INSERT INTO provider(id, "name")VALUES ((SELECT nextval('provider_id_seq'), "Sothebys");

INSERT INTO ratingagency(id, ratingagencyname, maxpoints)VALUES ((SELECT nextval('ratingagency_id_seq'), 'Parker', 100);
INSERT INTO ratingagency(id, ratingagencyname, maxpoints)VALUES ((SELECT nextval('ratingagency_id_seq'), 'Gabriel', 20);
INSERT INTO ratingagency(id, ratingagencyname, maxpoints)VALUES ((SELECT nextval('ratingagency_id_seq'), 'Weinwisser', 100);
INSERT INTO ratingagency(id, ratingagencyname, maxpoints)VALUES ((SELECT nextval('ratingagency_id_seq'), 'Fallstaf', 100);

INSERT INTO unit(id,deciliters) VALUES ((SELECT nextval('unit_id_seq')),3.75);
INSERT INTO unit(id,deciliters) VALUES ((SELECT nextval('unit_id_seq')),7.5);
INSERT INTO unit(id,deciliters) VALUES ((SELECT nextval('unit_id_seq')),15);
INSERT INTO unit(id,deciliters) VALUES ((SELECT nextval('unit_id_seq')),30);
INSERT INTO unit(id,deciliters) VALUES ((SELECT nextval('unit_id_seq')),45);
INSERT INTO unit(id,deciliters) VALUES ((SELECT nextval('unit_id_seq')),60);
