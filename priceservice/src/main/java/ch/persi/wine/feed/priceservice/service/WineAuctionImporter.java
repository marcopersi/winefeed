package ch.persi.wine.feed.priceservice.service;

import ch.persi.wine.feed.priceservice.model.WineAuctionRow;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.sql.PreparedStatement;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Imports flat {@link WineAuctionRow} records into the normalized schema
 * (provider, unit, wine, offering, wine_offering).
 * <p>
 * A full reload is performed: the tables are cleared first, then rows are
 * inserted with in-memory deduplication of provider/unit/wine.
 */
@Component
public class WineAuctionImporter {

    private final JdbcTemplate jdbc;

    public WineAuctionImporter(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Transactional
    public void importRows(List<WineAuctionRow> rows) {
        clearTables();

        Map<String, Long> providers = new HashMap<>();
        Map<Double, Long> units = new HashMap<>();
        Map<String, Long> wines = new HashMap<>();

        for (WineAuctionRow row : rows) {
            String providerName = row.provider() == null ? "Unknown" : row.provider();
            long providerId = providers.computeIfAbsent(providerName, this::insertProvider);

            Double deciliters = row.deciliters() == null ? 0.0 : row.deciliters();
            long unitId = units.computeIfAbsent(deciliters, this::insertUnit);

            String wineKey = wineKey(row);
            long wineId = wines.computeIfAbsent(wineKey, key -> insertWine(row));

            long offeringId = insertOffering(providerId, row);
            insertWineOffering(wineId, offeringId, unitId, row.noOfBottles());
        }
    }

    private void clearTables() {
        jdbc.execute("DELETE FROM wine_offering");
        jdbc.execute("DELETE FROM offering");
        jdbc.execute("DELETE FROM wine");
        jdbc.execute("DELETE FROM unit");
        jdbc.execute("DELETE FROM provider");
    }

    private static String wineKey(WineAuctionRow row) {
        String producer = row.producer() == null ? "" : row.producer();
        String vintage = row.vintage() == null ? "" : row.vintage().toString();
        return row.name() + "|" + producer + "|" + vintage;
    }

    private long insertProvider(String name) {
        return insertWithGeneratedKey("INSERT INTO provider (name) VALUES (?)", ps -> ps.setString(1, name));
    }

    private long insertUnit(double deciliters) {
        return insertWithGeneratedKey("INSERT INTO unit (deciliters) VALUES (?)", ps -> ps.setDouble(1, deciliters));
    }

    private long insertWine(WineAuctionRow row) {
        return insertWithGeneratedKey(
                "INSERT INTO wine (name, producer, vintage, region, origin) VALUES (?, ?, ?, ?, ?)",
                ps -> {
                    ps.setString(1, row.name());
                    setStringOrNull(ps, 2, row.producer());
                    setIntOrNull(ps, 3, row.vintage());
                    setStringOrNull(ps, 4, row.region());
                    setStringOrNull(ps, 5, row.origin());
                });
    }

    private long insertOffering(long providerId, WineAuctionRow row) {
        return insertWithGeneratedKey(
                "INSERT INTO offering (provider_id, provider_offering_id, event_identifier, offering_date, "
                        + "price_min, price_max, realized_price, is_ohk, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ps -> {
                    ps.setLong(1, providerId);
                    setStringOrNull(ps, 2, row.providerOfferingId());
                    setStringOrNull(ps, 3, row.eventIdentifier());
                    if (row.offeringDate() != null) {
                        ps.setObject(4, row.offeringDate());
                    } else {
                        ps.setNull(4, java.sql.Types.DATE);
                    }
                    setDoubleOrNull(ps, 5, row.priceMin());
                    setDoubleOrNull(ps, 6, row.priceMax());
                    setDoubleOrNull(ps, 7, row.realizedPrice());
                    ps.setBoolean(8, Boolean.TRUE.equals(row.isOhk()));
                    setStringOrNull(ps, 9, row.note());
                });
    }

    private void insertWineOffering(long wineId, long offeringId, long unitId, Integer noOfBottles) {
        jdbc.update(
                "INSERT INTO wine_offering (wine_id, offering_id, unit_id, no_of_bottles) VALUES (?, ?, ?, ?)",
                wineId, offeringId, unitId, noOfBottles == null ? 1 : noOfBottles);
    }

    private long insertWithGeneratedKey(String sql, ParameterSetter setter) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbc.update(connection -> {
            PreparedStatement ps = connection.prepareStatement(sql, new String[]{"id"});
            setter.set(ps);
            return ps;
        }, keyHolder);
        Number key = keyHolder.getKey();
        if (key == null) {
            throw new IllegalStateException("No generated key returned for: " + sql);
        }
        return key.longValue();
    }

    private static void setStringOrNull(PreparedStatement ps, int index, String value) throws java.sql.SQLException {
        if (value == null) {
            ps.setNull(index, java.sql.Types.VARCHAR);
        } else {
            ps.setString(index, value);
        }
    }

    private static void setIntOrNull(PreparedStatement ps, int index, Integer value) throws java.sql.SQLException {
        if (value == null) {
            ps.setNull(index, java.sql.Types.INTEGER);
        } else {
            ps.setInt(index, value);
        }
    }

    private static void setDoubleOrNull(PreparedStatement ps, int index, Double value) throws java.sql.SQLException {
        if (value == null) {
            ps.setNull(index, java.sql.Types.NUMERIC);
        } else {
            ps.setDouble(index, value);
        }
    }

    @FunctionalInterface
    private interface ParameterSetter {
        void set(PreparedStatement ps) throws java.sql.SQLException;
    }
}
