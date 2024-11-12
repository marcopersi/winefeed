package ch.persi.java.vino.wermuth;

import ch.persi.java.vino.domain.Unit;
import ch.persi.java.vino.domain.WineOffering;
import ch.persi.java.vino.importers.Tuple2;
import ch.persi.java.vino.importers.wermuth.format2015.LotPriceInfo;
import ch.persi.java.vino.importers.wermuth.format2015.ResultFilebasedLotLinePreparer;
import ch.persi.java.vino.importers.wermuth.format2015.Wermuth2015ImportTask;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static ch.persi.java.vino.importers.wermuth.format2015.Wermuth2015ImportTask.aRecordLinePattern;
import static ch.persi.java.vino.importers.wermuth.format2015.Wermuth2015ImportTask.clean;
import static org.junit.jupiter.api.Assertions.*;

class WermuthPost2015Tests {


    @Test
    void testAnotherTest() {
        Pattern aPattern = Pattern.compile("^.*(MO, [a-zA-Zäüö ]*, ).*", Pattern.CASE_INSENSITIVE);
        Matcher matcher = aPattern.matcher("1 Chardonnay MO, Bündner Herrschaft, Martha und Daniel Gantenbein 1 Magnumflasche, 2010 pro Lot 400-600 480 ");
        String anOrigin = null;

        if (matcher.matches()) {
            String anOriginString = matcher.group(1);
            anOrigin = anOriginString.replace(",", " ");
        }
        assertNotNull(anOrigin);
    }

    @Test
    void testOriginExtraction() {
        String aTestString = "1 Chardonnay MO, Bündner Herrschaft, Martha und Daniel Gantenbein 1 Magnumflasche, 2010 pro Lot 400-600 480 ";
        Tuple2<String, String> processOrigin = Wermuth2015ImportTask.processOrigin(aTestString);
        assertNotNull(processOrigin.getKey());
        assertNotNull(processOrigin.getValue());
        assertEquals("MO Bündner Herrschaft", processOrigin.getKey().trim());
        assertEquals("1 Chardonnay, Martha und Daniel Gantenbein 1 Magnumflasche, 2010 pro Lot 400-600 480 ", processOrigin.getValue());
    }

    @Test
    void testLineRecognition() {
        String[] someLines = new String[24];
        someLines[0] = "88 Château Magdeleine 1 Dutzend Flaschen, 2000, 6er OHK pro Dz. CHF 660-840 680.00";
        someLines[1] = "135 Château Magrez Fombrauge 6 Flaschen, 2000, OHK pro Lot CHF 960-1200 900.00";
        someLines[2] = "181 Château Doisy Vèdrines 24 3/8 Flaschen, 1997, OHK pro Lot CHF 480-720 400.00";
        someLines[3] = "240 Cabernet Sauvignon “Bryant Family“ 1 Flasche, 1995 (Parker 99) pro Lot CHF 500-700 500.00";
        someLines[4] = "304 Riesling Auslese „Abtsberg“, Maximin Grünhäuser 1 Doppelmagnumflasche, 2006, OHK pro Lot CHF 120-200 160.00";
        someLines[5] = "1 Champagne Dom Pérignon 1 Flasche, 1996, OC pro Lot CHF 150-220 160.00";
        someLines[6] = "2 Château Pétrus 1 Dutzend Flaschen, 1996, OHK pro Lot CHF 18'000-24'000 32'000.00";
        someLines[7] = "4 Meursault 1 er cru «Charmes», Comtes Lafon 6 Flaschen, 2005 pro Lot CHF 900-1200 900.00";
        someLines[8] = "5 Corton Charlemagne, Raphet 2 Magnumflaschen, 2009 pro Lot CHF 300-500 -";
        someLines[9] = "6 Pommard 1 er cru “Les Epenots”, Domaine Parent 1 Dutzend Flaschen, 2005 pro Dz. CHF 600-840 -";
        someLines[10] = "155 Château Le Pin 1 Flasche, 1999 pro Lot CHF 1200-1800 1'000.00";
        someLines[11] = "230 Syrah “Eisele Vineyard”, Araujo 6 Flaschen, 1995 (Parker 97) pro Lot CHF 1200-1500 1'000.00";
        someLines[12] = "251 Cabernet Sauvignon “Hillside Select”, Shafer 3 Flaschen, 1997 pro Lot CHF 900-1200 900.00";
        someLines[13] = "307 Riesling GG „Forster Kirchenstück“, Dr. von Bassermann Jordan 1 Doppelmagnumflasche, 2009 pro Lot CHF 200-300 200.00";
        someLines[14] = "527 La Jota “15th Anniversary”, Cabernet Sauvignon 1 Imperialflasche, 1996 (Parker 96) pro Lot CHF 700-1000 1'000.00";
        someLines[15] = "694 Hermitage blanc, Tardieu-Laurent 1 Dutzend Flaschen 2004 pro Dz. CHF 240-360 220.00";
        someLines[16] = "11 Château Margaux 4 Flaschen, 1999, 1er OHK (E-leicht verschmutzt) pro Lot CHF 1200-1500 CHF 1'200.00";
        someLines[17] = "9 Château Poujeaux 1 Dutzend 3/8 Flaschen, 2000, OHK pro Dz. CHF 210-300 CHF 280.00";
        someLines[18] = "3 Meursault Charmes, Comtes Lafon 5 Flaschen, 2005 pro Lot 750-1000 750";
        someLines[19] = "12 Château Margaux 6 Flaschen, 2000,  (Parker 100) pro Lot 4200-5400 4'000.00";
        someLines[20] = "6 Pommard 1 er cru “Les Epenots”, Domaine Parent 1 Dutzend Flaschen, 2005 pro Dz. CHF 600-840 CHF -";
        someLines[21] = "185 Château d’Yquem, (Perfekter Zustand, Parker 98) 1 Imperialflasche, 1986, OHK pro Lot CHF 3000-5000 CHF 3'200.00";
        someLines[22] = "1 Château Canon La Gaffelière AC/MC, St. Emilion, 1 Dutzend Flaschen, 1998, OHK pro Lot 000-000 1020";
        someLines[23] = "1 Chardonnay, Martha und Daniel Gantenbein 1 Magnumflasche, 2010 pro Lot 400-600 480";

        for (String aLine : someLines) {
            Matcher matcher = Wermuth2015ImportTask.aRecordLinePattern.matcher(Wermuth2015ImportTask.clean(aLine));
            assertNotNull(matcher);
            assertTrue(matcher.matches());

            for (int i = 0; i <= matcher.groupCount(); i++) {
                System.out.println("group i " + i + ": " + matcher.group(i));
            }
        }
    }


    @Test
    void testBottleSize() {
        Map<String, Unit> someInput = new HashMap<>();
        someInput.put(" Doppelmagnumflasche,", new Unit(BigDecimal.valueOf(30)));
        someInput.put(" Magnumflasche", new Unit(BigDecimal.valueOf(15)));
        someInput.put(" Jeroboam", new Unit(BigDecimal.valueOf(45)));
        someInput.put(" Doppelmagnumflasche", new Unit(BigDecimal.valueOf(30)));
        someInput.put(" Flaschen", new Unit(BigDecimal.valueOf(7.5)));
        someInput.put(" 3/8 Flaschen", new Unit(BigDecimal.valueOf(3.75d)));
        someInput.put(" Flasche", new Unit(BigDecimal.valueOf(7.5)));

        for (Entry<String, Unit> anElement : someInput.entrySet()) {
            Unit aUnit = new Wermuth2015ImportTask().processBottleSize(anElement.getKey());
            assertEquals(aUnit.getDeciliters(), anElement.getValue().getDeciliters());
        }

    }

    @Test
    void testPricingInformation() {
        Map<String, LotPriceInfo> someInput = new HashMap<>();
        someInput.put("CHF 3000-5000 3'200.00", new LotPriceInfo(3000, 5000, 3200));
        someInput.put("CHF 600-840 - ", new LotPriceInfo(600, 840, 0));
        someInput.put("CHF 720-960 750.00", new LotPriceInfo(720, 960, 750));
        someInput.put("CHF 360-480 450.00", new LotPriceInfo(360, 480, 450));
        someInput.put("CHF 7'800-9500 12'750.00", new LotPriceInfo(7800, 9500, 12750));
        someInput.put("CHF 10-50 99.00", new LotPriceInfo(10, 50, 99));
        someInput.put("CHF 3000-5000 3200.00", new LotPriceInfo(3000, 5000, 3200));
        someInput.put("CHF 600-840 -", new LotPriceInfo(600, 840, 0));

        for (Entry<String, LotPriceInfo> anElement : someInput.entrySet()) {
            LotPriceInfo processLotPricing = Wermuth2015ImportTask.processLotPricing(Wermuth2015ImportTask.clean(anElement.getKey()));
            assertEquals(processLotPricing, anElement.getValue());
        }

    }

    @Test
    void testNoOfBottles() {
        Map<Tuple2<String, String>, Integer> someInput = new HashMap<>();
        someInput.put(new Tuple2<>("1", " pro Dz. "), 12);
        someInput.put(new Tuple2<>("6", " pro Lot "), 6);
        someInput.put(new Tuple2<>("21", " pro Lot "), 21);
        someInput.put(new Tuple2<>("2", " pro Dutzend "), 24);
        someInput.put(new Tuple2<>("1", " pro dz. "), 1);
        someInput.put(new Tuple2<>("1", " pro Dz "), 12);

        for (Entry<Tuple2<String, String>, Integer> anElement : someInput.entrySet()) {
            int aNoOfBottles = Wermuth2015ImportTask.processNoOfBottles(anElement.getKey().getKey(), anElement.getKey().getValue());
            assertEquals(aNoOfBottles, anElement.getValue().intValue());
        }
    }

    @SuppressWarnings("null")
    @Test
    void testLinePreparer() {

        List<String> someInput = new ArrayList<>();
        someInput.add("252 1 Champagne Dom Pérignon 1 Flasche, 1996, OC pro Lot CHF 150-220 CHF 160.00");
        someInput.add("252 2 Champagne Dom Pérignon 3 Flaschen, 1996, 1er OC pro Lot CHF 450-660 CHF 480.00");

        List<String> prepare = ResultFilebasedLotLinePreparer.prepare(someInput);
        assertEquals(2, prepare.size());
        String string = someInput.get(0);
        assertEquals(string.substring(4), prepare.get(0));

        String aSecondLine = someInput.get(1);
        assertEquals(aSecondLine.substring(4), prepare.get(1));
    }

    @Test
    void testMatchingGroups() {

        String aLineExpression = "11 Château Margaux 4 Flaschen, 1999,  OHK pro Lot  1200-1500  1'200.00";
        Matcher matcher = aRecordLinePattern.matcher(aLineExpression);

        assertTrue(matcher.matches(), "Pattern/line does not match");
        for (int i = 0; i < matcher.groupCount(); i++) {
            System.out.println("group: " + i + " is: " + matcher.group(i));
        }
    }

    @Test
    void testLineProcessing() {

        // preparing
        Wermuth2015ImportTask anImportTask = new Wermuth2015ImportTask();
        anImportTask.setAuctionDate(LocalDate.now());
        anImportTask.setEventIdentifier("WZ_TEST");

        // execution
        String aLine = "9 Château Poujeaux 1 Dutzend 3/8 Flaschen, 2000, OHK pro Dz. CHF 210-300 CHF 280.00";
        String aCleanedLine = clean(aLine);
        WineOffering aResultWineOffering = anImportTask.processLine(aCleanedLine);

        assertNotNull(aResultWineOffering);
        assertEquals(210, aResultWineOffering.getOffering().getPriceMin());
        assertEquals(300, aResultWineOffering.getOffering().getPriceMax());

        assertEquals(210, aResultWineOffering.getOffering().getPriceMin());
        assertEquals(300, aResultWineOffering.getOffering().getPriceMax());
        assertEquals(280, aResultWineOffering.getOffering().getRealizedPrice());
        assertEquals(2000, aResultWineOffering.getWine().getVintage());

        assertTrue(aResultWineOffering.getOffering().isOHK());
        assertEquals(12, aResultWineOffering.getOffering().getNoOfBottles());
        assertEquals("9", aResultWineOffering.getOffering().getProviderOfferingId());
        assertEquals(BigDecimal.valueOf(3.75), aResultWineOffering.getWineUnit().getDeciliters());

        //execution
        WineOffering aSecondWineRecord = anImportTask.processLine(clean("12 Château Margaux 6 Flaschen, 2000,  (Parker 100) pro Lot 4200-5400 4'000.00"));

        // asserting
        assertNotNull(aSecondWineRecord);
        assertNotNull(aSecondWineRecord.getOffering());
        assertNotNull(aSecondWineRecord.getWine());
        assertEquals(4200, aSecondWineRecord.getOffering().getPriceMin());
        assertEquals(5400, aSecondWineRecord.getOffering().getPriceMax());
        assertEquals(4000, aSecondWineRecord.getOffering().getRealizedPrice());
        assertEquals(2000, aSecondWineRecord.getWine().getVintage());
        assertFalse(aSecondWineRecord.getOffering().isOHK());
        assertEquals(6, aSecondWineRecord.getOffering().getNoOfBottles());
        assertEquals("12", aSecondWineRecord.getOffering().getProviderOfferingId());
        assertEquals(BigDecimal.valueOf(7.5),aSecondWineRecord.getWineUnit().getDeciliters());


        WineOffering aThirdWineRecord = anImportTask.processLine(clean("266 Cabernet Sauvignon Beckstoffer Tokalon, Schrader 6 Flaschen, 2000 pro Lot 900-1200 750"));

        // asserting
        assertNotNull(aThirdWineRecord);
        assertNotNull(aThirdWineRecord.getOffering());
        assertNotNull(aThirdWineRecord.getWine());
        assertEquals(900, aThirdWineRecord.getOffering().getPriceMin());
        assertEquals(1200, aThirdWineRecord.getOffering().getPriceMax());
        assertEquals(750, aThirdWineRecord.getOffering().getRealizedPrice());
        assertEquals(2000, aThirdWineRecord.getWine().getVintage());
        assertFalse(aThirdWineRecord.getOffering().isOHK());
        assertEquals(6, aThirdWineRecord.getOffering().getNoOfBottles());
        assertEquals("266", aThirdWineRecord.getOffering().getProviderOfferingId());
        assertEquals(aThirdWineRecord.getWineUnit().getDeciliters(), BigDecimal.valueOf(7.5));
    }


}
