package ch.persi.java.vino.importers;

import org.junit.Assert;
import org.junit.Test;

import java.time.LocalDate;

public class DateParsingStrategyTest {

    @Test
    public void testDateParsing() {
        LocalDate auctionDate = new DateParsingStrategy("21022021").getAuctionDate();
        Assert.assertNotNull(auctionDate);
        Assert.assertEquals(LocalDate.of(2021, 2, 21), auctionDate);
    }
}