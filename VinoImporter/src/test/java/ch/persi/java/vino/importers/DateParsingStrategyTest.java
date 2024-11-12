package ch.persi.java.vino.importers;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

public class DateParsingStrategyTest {

    @Test
    public void testDateParsing() {
        LocalDate auctionDate = new DateParsingStrategy("21022021").getAuctionDate();
        assertNotNull(auctionDate);
        assertEquals(LocalDate.of(2021, 2, 21), auctionDate);
    }
}
