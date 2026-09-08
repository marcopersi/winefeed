package ch.persi.wine.feed.priceservice.service;

import ch.persi.wine.feed.priceservice.model.WineAuctionRow;
import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.DataFormatter;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.Workbook;
import org.apache.poi.ss.usermodel.WorkbookFactory;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Reads the flat, quality-checked staging Excel files and turns them into
 * {@link WineAuctionRow} records. The column layout varies across sheets and
 * files (12/14/16 columns), so columns are addressed by header name.
 */
@Component
public class ExcelWineReader {

    private static final Pattern SHEET_NAME = Pattern.compile("^(.+?)_(\\d{2}\\.\\d{2}\\.\\d{4})$");
    private static final DateTimeFormatter SHEET_DATE = DateTimeFormatter.ofPattern("dd.MM.yyyy");
    private static final DateTimeFormatter ISO_DATE = DateTimeFormatter.ofPattern("yyyy-MM-dd");

    private static final Map<String, Double> BOTTLE_SIZE_DL = Map.ofEntries(
            Map.entry("flasche", 7.5), Map.entry("bottle", 7.5), Map.entry("bouteille", 7.5),
            Map.entry("halbe", 3.75), Map.entry("halfbottle", 3.75), Map.entry("demi", 3.75),
            Map.entry("magnum", 15.0), Map.entry("doppelmagnum", 30.0),
            Map.entry("jeroboam", 45.0), Map.entry("imperial", 60.0),
            Map.entry("salmanazar", 90.0), Map.entry("balthazar", 120.0),
            Map.entry("nebuchadnezzar", 150.0), Map.entry("melchior", 180.0));

    private final DataFormatter formatter = new DataFormatter();

    public List<WineAuctionRow> read(Path file) throws IOException {
        List<WineAuctionRow> rows = new ArrayList<>();
        try (Workbook workbook = WorkbookFactory.create(Files.newInputStream(file))) {
            for (Sheet sheet : workbook) {
                rows.addAll(readSheet(sheet));
            }
        }
        return rows;
    }

    private List<WineAuctionRow> readSheet(Sheet sheet) {
        List<WineAuctionRow> rows = new ArrayList<>();

        Row header = sheet.getRow(0);
        if (header == null) {
            return rows;
        }

        Map<String, Integer> index = new HashMap<>();
        for (Cell cell : header) {
            String name = formatter.formatCellValue(cell).trim();
            if (!name.isEmpty() && !name.startsWith("Unnamed")) {
                index.putIfAbsent(name, cell.getColumnIndex());
            }
        }

        if (!index.containsKey("name")) {
            return rows;
        }

        LocalDate sheetDate = parseSheetDate(sheet.getSheetName());

        for (int r = 1; r <= sheet.getLastRowNum(); r++) {
            Row row = sheet.getRow(r);
            if (row == null) {
                continue;
            }
            String name = stringValue(row, index, "name");
            if (name == null || name.isBlank()) {
                continue;
            }
            rows.add(toRow(row, index, sheetDate));
        }
        return rows;
    }

    private WineAuctionRow toRow(Row row, Map<String, Integer> index, LocalDate sheetDate) {
        LocalDate offeringDate = parseDate(stringValue(row, index, "offeringDate"));
        if (offeringDate == null) {
            offeringDate = sheetDate;
        }

        String provider = stringValue(row, index, "provider");
        if (provider == null || provider.isBlank()) {
            provider = parseSheetName(row.getSheet().getSheetName());
        }

        return new WineAuctionRow(
                stringValue(row, index, "name"),
                stringValue(row, index, "producer"),
                stringValue(row, index, "region"),
                stringValue(row, index, "origin"),
                intValue(row, index, "vintage"),
                decilitersValue(row, index, "deciliters"),
                intValue(row, index, "noOfBottles"),
                stringValue(row, index, "providerOfferingId"),
                stringValue(row, index, "eventIdentifier"),
                offeringDate,
                booleanValue(row, index, "isOHK"),
                doubleValue(row, index, "priceMin"),
                doubleValue(row, index, "priceMax"),
                doubleValue(row, index, "realizedPrice"),
                provider,
                stringValue(row, index, "note")
        );
    }

    private String stringValue(Row row, Map<String, Integer> index, String column) {
        Integer i = index.get(column);
        if (i == null) {
            return null;
        }
        Cell cell = row.getCell(i);
        if (cell == null) {
            return null;
        }
        String value = formatter.formatCellValue(cell).trim();
        return value.isEmpty() ? null : value;
    }

    private Integer intValue(Row row, Map<String, Integer> index, String column) {
        String value = stringValue(row, index, column);
        if (value == null) {
            return null;
        }
        try {
            double parsed = Double.parseDouble(value.replace("'", ""));
            return (int) parsed;
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private Double doubleValue(Row row, Map<String, Integer> index, String column) {
        String value = stringValue(row, index, column);
        if (value == null) {
            return null;
        }
        try {
            return Double.parseDouble(value.replace("'", "").replace(",", "."));
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private Double decilitersValue(Row row, Map<String, Integer> index, String column) {
        Double numeric = doubleValue(row, index, column);
        if (numeric != null) {
            return numeric;
        }
        String value = stringValue(row, index, column);
        if (value == null) {
            return null;
        }
        return BOTTLE_SIZE_DL.get(value.toLowerCase());
    }

    private Boolean booleanValue(Row row, Map<String, Integer> index, String column) {
        String value = stringValue(row, index, column);
        if (value == null) {
            return null;
        }
        return value.equalsIgnoreCase("TRUE") || value.equalsIgnoreCase("YES");
    }

    private static LocalDate parseSheetDate(String sheetName) {
        Matcher matcher = SHEET_NAME.matcher(sheetName.trim());
        if (matcher.matches()) {
            try {
                return LocalDate.parse(matcher.group(2), SHEET_DATE);
            } catch (DateTimeParseException ignored) {
                // fall through
            }
        }
        return null;
    }

    private static String parseSheetName(String sheetName) {
        Matcher matcher = SHEET_NAME.matcher(sheetName.trim());
        if (matcher.matches()) {
            return matcher.group(1).trim();
        }
        return null;
    }

    private static LocalDate parseDate(String value) {
        if (value == null) {
            return null;
        }
        try {
            return LocalDate.parse(value, ISO_DATE);
        } catch (DateTimeParseException ignored) {
            try {
                return LocalDate.parse(value, SHEET_DATE);
            } catch (DateTimeParseException e) {
                return null;
            }
        }
    }
}
