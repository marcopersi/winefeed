package ch.persi.java.vino.wermuth;

import java.io.File;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;

import org.junit.Assert;
import org.junit.Test;

import ch.persi.java.vino.importers.wermuth.formatpre2015.WermuthPre2015DateExtractingStrategy;
import ch.persi.java.vino.importers.wermuth.formatpre2015.WermuthPre2015ImportTask;
import ch.persi.java.vino.importers.wermuth.formatpre2015.WermuthRecordLineExtractor;
import ch.persi.java.vino.importers.wermuth.prices.WermuthPricePageParser;
import ch.persi.java.vino.util.WermuthParser;

public class WermuthPre2015Tests {

	@Test
	public void testExtractRealizedPrice() {
		Map<String, Integer> someInput = new HashMap<>();
		someInput.put("1 57 Flaschen, 2007, Einzel-OHK pro Lot Sfr. 440-600 600", 600);
		someInput.put("620 Lodovico 1 Doppelmagnumflasche, 2008, OHK pro Lot Sfr. 1000-1400 1'100.00 SFr.", 1100);
		someInput.put("61 Matarocchio 1 Magnumflasche, 2007, OHK pro Lot Sfr. 500-700 - SFr.", null);
		someInput.put("62 Lodovico 1 Doppelmagnumflasche, 2008, OHK pro Lot Sfr. 1'000-1'400 1'500.00 SFr.", 1500);
		someInput.put("1234 Lodovico 1 Doppelmagnumflasche, 2012, pro Lot Sfr. 1'000-1'400 1700.00 SFr.", 1700);
		someInput.put("88 Lodovico 1 Doppelmagnumflasche, 2008, OHK pro Lot CHF 1'000-1'400 1'500.00", 1500);

		for (Entry<String, Integer> aLine : someInput.entrySet()) {
			Assert.assertEquals(aLine.getValue(), WermuthPricePageParser.getRealizedPrice(aLine.getKey()));
		}
	}


	@Test
	public void testSuccessfullRecordLines()
	{
		List<String> someRecordLines = new ArrayList<>();
		
		someRecordLines.add("1 3 Flaschen, 1982, Niv. TS pro Lot Sfr 1800-3300");
		someRecordLines.add("22 53 Magnumflaschen, 1986, OHK pro Lot Sfr. 750-900");
		someRecordLines.add("4 3 MagnumFlaschen, 1990, OHK pro Lot Sfr. 1200-1500");
		someRecordLines.add("900 1 Dutzend Flaschen, 1990, OHK pro Dz. Sfr 1080-1440");
		someRecordLines.add("1234 1 Dutzend Flaschen, 1990, OHK pro Dz. Sfr 1080-1440");
		someRecordLines.add("397 24 3/8-Flaschen, 1996, OHK pro Lot Sfr. 300-420");
		someRecordLines.add("394 1 MagnumFlasche, 1997, OHK 	pro Lot	Sfr. 380-450");
		someRecordLines.add("156 4 DoppelmagnumFlasche, 1985	pro Lot	Sfr. 400-560");
		someRecordLines.add("1 1 Dutzend Flaschen, 1975, OHK pro Dz. Sfr. 960-1200");
		
		for (String aLine : someRecordLines) {
			boolean recordLine = new WermuthRecordLineExtractor(aLine).isRecordLine();
			System.out.println("Line: " + aLine + " is evaluated as: " + recordLine);
			Assert.assertTrue(recordLine);
		}
	}

	@Test
	public void testGetNumberOfBottles()
	{
		Map<String,Integer> someInput = new HashMap<>();
		someInput.put("1 2 3/8 Flaschen, 2007, Einzel-OHK pro Lot Sfr 440-600", 2);
		someInput.put("11 57 Flaschen, 2007, Einzel-OHK pro Lot Sfr. 440-600", 57);
		someInput.put("7211 1 Dutzend Flaschen, 2000, OHK pro Lot Sfr 1320-1560", 12);
		someInput.put("720 2 Dutzend Flaschen, 2005, OHK pro Lot Sfr. 1440-1800", 24);

		for (Entry<String, Integer> aLine : someInput.entrySet()) {
			Integer aNoOfBottles = new WermuthRecordLineExtractor(aLine.getKey()).getNoOfBottles();
			System.out.println("The no of bottles in Line: " + aLine + " is considered to be: " + aNoOfBottles);
			Assert.assertEquals(aLine.getValue(), aNoOfBottles);
		}
	}
	
	@Test
	public void testFailingRecordLines()
	{
		List<String> someRecordLines = new ArrayList<>();
		someRecordLines.add("322 Total 6 Flaschen pro Lot Sfr. 180-240");
		someRecordLines.add("617 6 Flaschen pro Lot Sfr. 400-800");
		someRecordLines.add("618 Total 7 Flaschen pro Lot Sfr. 1100-1600");
		someRecordLines.add("653 Total 24 Flaschen pro Lot Sfr. 240-480");

		for (String aLine : someRecordLines) {
			boolean recordLine = new WermuthRecordLineExtractor(aLine).isRecordLine();
			System.out.println("Line: " + aLine + " is evaluated as: " + recordLine);
			Assert.assertFalse(recordLine);
		}
	}
	
	@Test
	public void testSizes()
	{
		Map<String,BigDecimal> someInput = new HashMap<>();
		someInput.put("711 2 3/8 Flaschen, 2007, Einzel-OHK pro Lot Sfr. 440-600", BigDecimal.valueOf(3.75));
		someInput.put("720 6 Magnumflaschen, 2005, OHK pro Lot Sfr. 1440-1800", BigDecimal.valueOf(15));
		someInput.put("721 1 Dutzend Flaschen, 2000, OHK pro Lot Sfr. 1320-1560", BigDecimal.valueOf(7.5));
		someInput.put("4 3 MagnumFlaschen, 1990, OHK pro Lot Sfr. 1200-1500", BigDecimal.valueOf(15));
		someInput.put("156	4 DoppelmagnumFlasche, 1985	pro Lot	Sfr. 400-560", BigDecimal.valueOf(30));


		WermuthPre2015ImportTask wermuthImportTask = new WermuthPre2015ImportTask();
		for (Entry<String, BigDecimal> aLine : someInput.entrySet()) {
			BigDecimal aSize = wermuthImportTask.determineSize(aLine.getKey());
			System.out.println("Bottle size of Line: " + aLine + " is determined as: " + aSize);
			Assert.assertEquals(aLine.getValue(), aSize);
		}
	}
	
	@Test
	public void testVintages()
	{
		Map<String,Integer> someInput = new HashMap<>();
		someInput.put("1 2 3/8 Flaschen, 2007, Einzel-OHK pro Lot Sfr. 440-600", 2007);
		someInput.put("111 61 Magnumflaschen, 2005, OHK pro Lot Sfr. 1440-1800", 2005);
		someInput.put("1111 157 Dutzend Flaschen, 2000, OHK pro Lot Sfr. 1320-1560", 2000);

		for (Entry<String, Integer> aLine : someInput.entrySet()) {
			Integer aVintage = new WermuthRecordLineExtractor(aLine.getKey()).getVintage();
			System.out.println("Vintage of Line: " + aLine + " is: " + aVintage);
			Assert.assertEquals(aLine.getValue(), aVintage);
		}
	}
	
	@Test
	public void testOrigins()
	{
		Map<String,String> someInput = new HashMap<>();
		someInput.put("AC/MC, St. Julien, 2e grand cru classé (1)", "AC/MC");
		someInput.put("DO/MO, Priorat, Alvaro Palacio", "DO/MO");
		someInput.put("AC/MC, St. Estéphe, 3e grand cru classé", "AC/MC");
		someInput.put("AC/MO, CÃ´te de Nuits, Grand cru, Domaine RomanÃ©e Conti", "AC/MO");
		someInput.put("MO/DOCa, Rioja, Bodegas Artadi", "MO/DOCa");
		someInput.put("MO/DOCA, Priorat, Celler Mas Doix", "MO/DOCA");
		someInput.put("MO/DOCG, Piemont, Fratelli Giacosa", "MO/DOCG");
		someInput.put("MO/IGT, Emilia Romagna, Tenuta Zerbina", "MO/IGT");
		someInput.put("MO, Napa Valley, Pahlmeyer", "MO");
		someInput.put("AC/EA, Rheingau, Weingut Dànnhoff", "AC/EA");
		someInput.put("MO/DOC, Bolgheri, Tenuta San Guido", "MO/DOC");
		
		for (Entry<String, String> aLine : someInput.entrySet()) {
			String anOrigin = WermuthPre2015ImportTask.getOrigin(aLine.getKey());
			System.out.println("Origin of Line: " + aLine + " is evaluated as: " + anOrigin);
			Assert.assertEquals(aLine.getValue(), anOrigin);
		}
	}

	@Test
	public void testGetAuctionDate() {
		List<String> someLines = new WermuthParser().parse(new File("prototyping/resources/223.pdf").getAbsolutePath());
		LocalDate aDate = new WermuthPre2015DateExtractingStrategy(someLines).getAuctionDate();
		Assert.assertNotNull(aDate);
	}

    @Test
    public void testIsRecordLine()
    {
    	String[] someRecordLines = new String[]{"1 1 Magnumflasche 1995, pro Lot Sfr. 340-500",
    			"16 1 Doppelmagnumflasche, 1997, OHK pro Lot Sfr. 500-700",
    	    	"169 1 Imperialflasche, 2007, OHK pro Lot Sfr. 800-1200",
    	    	"174 3 Flaschen, 2001 pro Lot Sfr. 1800-2100",
    	    	"185 1 Flasche, 2008 pro Dz. Sfr. 1200-1800",
    	    	"187 1 Dutzend Flaschen, 2008, OHK pro Dz. Sfr. 900-1200",
    	    	"230 1 Dutzend Flaschen, 1997, 6er OHK pro Dz. Sfr. 840-1080",
    	    	"246 1 Impérialflasche, 2000, OHK pro Lot Sfr. 1200-1500",
    	    	"252 1 Jeroboamflasche, 1990, OHK pro Lot Sfr. 2400-3000",
    	    	"323 2 3/8 Flaschen, 2000 pro Lot Sfr. 200-350",
    	    	"334 6 Flaschen, 2002, OC pro Lot Sfr. 360-480",
    	    	"486 12 3/8 Flaschen, 2001, OHK pro Lot Sfr. 390-480",
    	    	"583 6 Flaschen, 2005, 3er OHK pro Lot Sfr. 540-720",
    	    	"984 2 Flaschen, 1966 pro Lot Sfr. 300-500",
    	    	"326 Total 6 3/8 Flaschen, 1998 pro Lot Sfr. 480-720"};
    	
    	for (String aTestRecordLine : someRecordLines) {
			boolean recordLine = new WermuthRecordLineExtractor(aTestRecordLine).isRecordLine();
			Assert.assertTrue(aTestRecordLine + " isn't recognized as recordLine !", recordLine);
		}
    }

	@Test
	public void testGetProducer() {
		String aTestOriginContainingProducerLine = "MO/DOC, Toscana, Cantina Constanti";
		Assert.assertNotNull(new WermuthPre2015ImportTask().getProducer("MO/DOC", aTestOriginContainingProducerLine));
	}

	@Test
	public void testGetOrigin() {
		String aMODOCOrigin = "MO/DOC, Toscana, Cantina Constanti";
		Assert.assertEquals("MO/DOC", WermuthPre2015ImportTask.getOrigin(aMODOCOrigin));

		String aMOIGTOrigin = "MO/IGT, Toscana, Antinori";
		Assert.assertEquals("MO/IGT", WermuthPre2015ImportTask.getOrigin(aMOIGTOrigin));

		String aMoDOCGOrigin = "MO/DOCG, Piemont, Aldo Conterno";
		Assert.assertEquals("MO/DOCG", WermuthPre2015ImportTask.getOrigin(aMoDOCGOrigin));

		String aMOOrigin = "MO, Napa Valley, Mondavi/Rothschild";
		Assert.assertEquals("MO", WermuthPre2015ImportTask.getOrigin(aMOOrigin));

		String aACMCOrigin = "AC/MC, Margaux, 1er grand cru classe";
		Assert.assertEquals("AC/MC", WermuthPre2015ImportTask.getOrigin(aACMCOrigin));

		String aDOMOOrigin = "DO/MO, Priorat, Alvaro Palacio";
		Assert.assertEquals("DO/MO", WermuthPre2015ImportTask.getOrigin(aDOMOOrigin));

		String aACEAOrigin = "AC/EA, Rheingau, Weingut Mönchhoff";
		Assert.assertEquals("AC/EA", WermuthPre2015ImportTask.getOrigin(aACEAOrigin));

		String anACMOOrigin = "AC/MO, Champagne, Armand de Brignac (Cattier)";
		Assert.assertEquals("AC/MO", WermuthPre2015ImportTask.getOrigin(anACMOOrigin));
	}

    @Test
    public void testGetNoOfBottles()
    {
    	Map<String,Integer> linesAndAssertValues = new HashMap<>();
    	
    	linesAndAssertValues.put("116 1 Magnumflasche 1995, pro Lot Sfr. 340-500", 1);
    	linesAndAssertValues.put("168 1 Doppelmagnumflasche, 1997, OHK pro Lot Sfr. 500-700", 1);
    	linesAndAssertValues.put("169 1 Imperialflasche, 2007, OHK pro Lot Sfr. 800-1200", 1);
    	linesAndAssertValues.put("174 3 Flaschen, 2001 pro Lot Sfr. 1800-2100", 3);
    	linesAndAssertValues.put("185 1 Flasche, 2008 pro Dz. Sfr. 1200-1800", 1);
    	linesAndAssertValues.put("187 1 Dutzend Flaschen, 2008, OHK pro Dz. Sfr. 900-1200", 12);
    	linesAndAssertValues.put("230 1 Dutzend Flaschen, 1997, 6er OHK pro Dz. Sfr. 840-1080", 12);
    	linesAndAssertValues.put("246 1 Impérialflasche, 2000, OHK pro Lot Sfr. 1200-1500", 1);
    	linesAndAssertValues.put("252 1 Jeroboamflasche, 1990, OHK pro Lot Sfr. 2400-3000", 1);
    	linesAndAssertValues.put("323 2 3/8 Flaschen, 2000 pro Lot Sfr. 200-350", 2);
    	linesAndAssertValues.put("334 6 Flaschen, 2002, OC pro Lot Sfr. 360-480", 6);
    	linesAndAssertValues.put("486 12 3/8 Flaschen, 2001, OHK pro Lot Sfr. 390-480",12);
    	linesAndAssertValues.put("583 6 Flaschen, 2005, 3er OHK pro Lot Sfr. 540-720",6);
    	linesAndAssertValues.put("984 2 Flaschen, 1966 pro Lot Sfr. 300-500", 2);
    	linesAndAssertValues.put("326 Total 6 3/8 Flaschen, 1998 pro Lot Sfr. 480-720",6);
    
    	for (Entry<String, Integer> aTestEntry : linesAndAssertValues.entrySet()) {
			Assert.assertEquals(aTestEntry.getValue(), new WermuthRecordLineExtractor(aTestEntry.getKey()).getNoOfBottles());
		}
    }
    
    @Test
    public void testGetVintage()
    {
    	Map<String,Integer> linesAndAssertValues = new HashMap<>();
    	
    	linesAndAssertValues.put("116 1 Magnumflasche 1995, pro Lot Sfr. 340-500", 1995);
    	linesAndAssertValues.put("168 1 Doppelmagnumflasche, 1997, OHK pro Lot Sfr. 500-700", 1997);
    	linesAndAssertValues.put("169 1 Imperialflasche, 2007, OHK pro Lot Sfr. 800-1200", 2007);
    	linesAndAssertValues.put("174 3 Flaschen, 2001 pro Lot Sfr. 1800-2100", 2001);
    	linesAndAssertValues.put("185 1 Flasche, 2008 pro Dz. Sfr. 1200-1800", 2008);
    	linesAndAssertValues.put("187 1 Dutzend Flaschen, 2008, OHK pro Dz. Sfr. 900-1200", 2008);
    	linesAndAssertValues.put("230 1 Dutzend Flaschen, 1997, 6er OHK pro Dz. Sfr. 840-1080", 1997);
    	linesAndAssertValues.put("246 1 Impérialflasche, 2000, OHK pro Lot Sfr. 1200-1500", 2000);
    	linesAndAssertValues.put("252 1 Jeroboamflasche, 1990, OHK pro Lot Sfr. 2400-3000", 1990);
    	linesAndAssertValues.put("323 2 3/8 Flaschen, 2000 pro Lot Sfr. 200-350", 2000);
    	linesAndAssertValues.put("334 6 Flaschen, 2002, OC pro Lot Sfr. 360-480", 2002);
    	linesAndAssertValues.put("486 12 3/8 Flaschen, 2001, OHK pro Lot Sfr. 390-480",2001);
    	linesAndAssertValues.put("583 6 Flaschen, 2005, 3er OHK pro Lot Sfr. 540-720",2005);
    	linesAndAssertValues.put("984 2 Flaschen, 1966 pro Lot Sfr. 300-500", 1966);
    	linesAndAssertValues.put("326 Total 6 3/8 Flaschen, 1998 pro Lot Sfr. 480-720",1998);
    
    	for (Entry<String, Integer> aTestEntry : linesAndAssertValues.entrySet()) {
			Assert.assertEquals(new WermuthRecordLineExtractor(aTestEntry.getKey()).getVintage(), aTestEntry.getValue());
		}
    }

	@Test
	public void testGetUnit() {
		Map<String, BigDecimal> linesAndAssertValues = new HashMap<>();

		linesAndAssertValues.put("116 1 Magnumflasche 1995, pro Lot Sfr. 340-500", new BigDecimal(15));
		linesAndAssertValues.put("168 1 Doppelmagnumflasche, 1997, OHK pro Lot Sfr 500-700", new BigDecimal(30));
		linesAndAssertValues.put("169 1 Imperialflasche, 2007, OHK pro Lot Sfr. 800-1200", new BigDecimal(60));
		linesAndAssertValues.put("174 3 Flaschen, 2001 pro Lot Sfr. 1800-2100", new BigDecimal("7.5"));
		linesAndAssertValues.put("185 1 Flasche, 2008 pro Dz. Sfr. 1200-1800", new BigDecimal("7.5"));
		linesAndAssertValues.put("187 1 Dutzend Flaschen, 2008, OHK pro Dz. Sfr 900-1200", new BigDecimal("7.5"));
		linesAndAssertValues.put("230 1 Dutzend Flaschen, 1997, 6er OHK pro Dz. Sfr. 840-1080", new BigDecimal("7.5"));
		linesAndAssertValues.put("246 1 Impérialflasche, 2000, OHK pro Lot Sfr 1200-1500", new BigDecimal(60));
		linesAndAssertValues.put("252 1 Jeroboamflasche, 1990, OHK pro Lot Sfr 2400 - 3000", new BigDecimal(45));
		linesAndAssertValues.put("253 1 Jéroboamflasche, 1990, OHK pro Lot Sfr 2400-3000", new BigDecimal(45));
		linesAndAssertValues.put("323 2 3/8 Flaschen, 2000 pro Lot Sfr. 200-350", new BigDecimal("3.75"));
		linesAndAssertValues.put("334 6 Flaschen, 2002, OC pro Lot Sfr. 360-480", new BigDecimal("7.5"));
		linesAndAssertValues.put("486 12 3/8 Flaschen, 2001, OHK pro Lot Sfr. 390-480", new BigDecimal("3.75"));
		linesAndAssertValues.put("583 6 Flaschen, 2005, 3er OHK pro Lot Sfr. 540-720", new BigDecimal("7.5"));
		linesAndAssertValues.put("984 2 Flaschen, 1966 pro Lot Sfr. 300-500", new BigDecimal("7.5"));
		linesAndAssertValues.put("326 Total 6 3/8 Flaschen, 1998 pro Lot Sfr. 480-720", new BigDecimal("3.75"));

		WermuthPre2015ImportTask wermuthImportTask = new WermuthPre2015ImportTask();
		for (Entry<String, BigDecimal> aTestEntry : linesAndAssertValues.entrySet()) {
			Assert.assertEquals("tryin: " + aTestEntry.getKey(), aTestEntry.getValue(), wermuthImportTask.determineSize(aTestEntry.getKey()));
		}
	}

	@Test
	public void testGetLotNumber() {
		Map<String, String> linesAndAssertValues = new HashMap<>();
		linesAndAssertValues.put("1 2 3/8 Flaschen, 2007, Einzel-OHK pro Lot Sfr. 440-600", "1");
		linesAndAssertValues.put("11 2 3/8 Flaschen, 2007, Einzel-OHK pro Lot Sfr. 440-600", "11");
		linesAndAssertValues.put("720 6 Magnumflaschen, 2005, OHK pro Lot Sfr. 1440-1800", "720");
		linesAndAssertValues.put("7211 1 Dutzend Flaschen, 2000, OHK pro Lot Sfr. 1320-1560", "7211");
		linesAndAssertValues.put("1 1 Magnumflasche 1995, pro Lot Sfr. 340-500", "1");
    	linesAndAssertValues.put("11 1 Doppelmagnumflasche, 1997, OHK pro Lot Sfr. 500-700", "11");
    	linesAndAssertValues.put("111 1 Imperialflasche, 2007, OHK pro Lot Sfr. 800-1200", "111");
    	linesAndAssertValues.put("1111 3 Flaschen, 2001 pro Lot Sfr. 1800-2100", "1111");
    
    	for (Entry<String, String> aTestEntry : linesAndAssertValues.entrySet()) {
			Assert.assertEquals(aTestEntry.getValue(), new WermuthRecordLineExtractor(aTestEntry.getKey()).getLotNumber());
		}
    }
    
    @Test
    public void testGetPriceMinimum()
    {
    	Map<String,Integer> linesAndAssertValues = new HashMap<>();
    	linesAndAssertValues.put("1 1 Magnumflasche 1995, pro Lot Sfr. 34-50", 34);
    	linesAndAssertValues.put("1 2 3/8 Flaschen, 2007, Einzel-OHK pro Lot Sfr 440- 600", 440);
    	linesAndAssertValues.put("720 6 Magnumflaschen, 2005, OHK pro Lot Sfr. 1440 -1800", 1440);
    	linesAndAssertValues.put("7211 1 Dutzend Flaschen, 2000, OHK pro Lot Sfr 13200 - 15600", 13200);
    	linesAndAssertValues.put("1 3 Flaschen, 1982, Sfr 1800 - 3300", 1800);
    	linesAndAssertValues.put("21 Chateau Clos St-Martin 1 Dutzend Flaschen, 2006, 6er OHK pro Dz. Sfr. 600-960 - SFr.", 600);

    
    	for (Entry<String, Integer> aTestEntry : linesAndAssertValues.entrySet()) {
			Assert.assertEquals(aTestEntry.getValue(), new WermuthRecordLineExtractor(aTestEntry.getKey()).getMinPrice());
		}
    }
    
    @Test
    public void testGetPriceMaximum()
    {
    	Map<String,Integer> linesAndAssertValues = new HashMap<>();
    	linesAndAssertValues.put("1 1 Magnumflasche 1995, pro Lot Sfr. 34-50", 50);
		linesAndAssertValues.put("1 2 3/8 Flaschen, 2007, Einzel-OHK pro Lot Sfr. 440- 600", 600);
		linesAndAssertValues.put("720 6 Magnumflaschen, 2005, OHK pro Lot Sfr. 1440 -1800", 1800);
		linesAndAssertValues.put("7211 1 Dutzend Flaschen, 2000, OHK pro Lot Sfr. 13200 - 15600", 15600);
    	linesAndAssertValues.put("1 3 Flaschen, 1982, Niv. TS pro Lot Sfr 1800 - 3300", 3300);
    	linesAndAssertValues.put("21 Château Clos St-Martin 1 Dutzend Flaschen, 2006, 6er OHK pro Dz. Sfr. 600-960 - SFr.", 960);
    
    	for (Entry<String, Integer> aTestEntry : linesAndAssertValues.entrySet()) {
			Assert.assertEquals(aTestEntry.getValue(), new WermuthRecordLineExtractor(aTestEntry.getKey()).getMaxPrice());
		}
    }
    
}
