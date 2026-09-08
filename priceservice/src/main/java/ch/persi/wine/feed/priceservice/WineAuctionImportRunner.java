package ch.persi.wine.feed.priceservice;

import ch.persi.wine.feed.priceservice.model.WineAuctionRow;
import ch.persi.wine.feed.priceservice.service.ExcelWineReader;
import ch.persi.wine.feed.priceservice.service.WineAuctionImporter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * Imports staging Excel files when {@code priceservice.import.files} is set
 * (comma-separated file paths). Intended to run as a one-off:
 * {@code --spring.main.web-application-type=none --priceservice.import.files=/a.xlsx,/b.xlsx}.
 */
@Component
public class WineAuctionImportRunner implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(WineAuctionImportRunner.class);

    private final ExcelWineReader reader;
    private final WineAuctionImporter importer;

    @Value("${priceservice.import.files:}")
    private String files;

    public WineAuctionImportRunner(ExcelWineReader reader, WineAuctionImporter importer) {
        this.reader = reader;
        this.importer = importer;
    }

    @Override
    public void run(String... args) throws Exception {
        if (files == null || files.isBlank()) {
            log.info("No import files configured (priceservice.import.files is empty). Skipping import.");
            return;
        }

        List<WineAuctionRow> allRows = new ArrayList<>();
        for (String file : files.split(",")) {
            Path path = Path.of(file.trim());
            log.info("Reading {}", path);
            List<WineAuctionRow> rows = reader.read(path);
            log.info("Read {} rows from {}", rows.size(), path);
            allRows.addAll(rows);
        }

        importer.importRows(allRows);
        log.info("Imported {} rows in total", allRows.size());
    }
}
