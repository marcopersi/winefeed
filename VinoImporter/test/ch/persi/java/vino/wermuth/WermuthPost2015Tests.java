package ch.persi.java.vino.wermuth;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;
import java.util.Map.Entry;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.junit.Test;

import ch.persi.java.vino.domain.Unit;
import ch.persi.java.vino.importers.Tuple2;
import ch.persi.java.vino.importers.wermuth.format2015.LotPriceInfo;
import ch.persi.java.vino.importers.wermuth.format2015.Wermuth2015ImportTask;
import junit.framework.TestCase;

public class WermuthPost2015Tests extends TestCase {

//	private Pattern compile = Pattern.compile("^([0-9]{1,4})\\s(.*)\\s([0-9]{1,3})(.*)([0-9]{4}.)(.*)(CHF.*$).*");
	private Pattern aPattern= Pattern.compile("^([0-9]{1,4})\\s(.*)\\s([0-9]{1,3})((.*[fF]lasche.*),?)\\s([0-9]{4}.),?(.*)(CHF.*$).*");

	@Test
	public void testLineRecognition() {
		String[] someLines = new String[16];
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

		
		for (String aLine : someLines) {
			Matcher matcher = aPattern.matcher(aLine);
			assertTrue(matcher.matches());
			
			for (int i = 0; i<=matcher.groupCount();i++)
			{
				System.out.println("group i " + i + ": " + matcher.group(i));
			}
		}
	}
	
//	@Test
//	public void testDifficultLines()
//	{
//		Pattern aMoreAdvancedPattern= Pattern.compile("^([0-9]{1,4})\\s(.*)\\s([0-9]{1,3})((.*[fF]lasche.*),?)\\s([0-9]{4}.),?(.*)(CHF.*$).*");
//
//		String[] someLines = new String[2];
//		someLines[0] = "266 Cabernet Sauvignon “Beckstoffer Tokalon”, Schrader 6 Flaschen, 2000 pro Lot CHF 900-1200 750.00";
//		someLines[1] = "344 Château Suduiraut Total 4 Magnumflaschen, 1988 pro Lot CHF 400-600 -";
//		
//		for (String aLine : someLines) {
//			Matcher matcher = aMoreAdvancedPattern.matcher(aLine);
//			assertTrue(matcher.matches());
//			System.out.println("LotNo:" + matcher.group(1) + "; wine: " + matcher.group(2) + "; NoBottles: "+  matcher.group(3) + "; vintage: " + matcher.group(6) + "; bottleSize: " + matcher.group(5) + " pricing: " + matcher.group(8));
//		}
//		
//	}

	@Test
	public void testBottleSize()
	{
		Map<String,Unit> someInput = new HashMap<>();
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
	public void testPricingInformation()
	{
		Map<String,LotPriceInfo> someInput = new HashMap<>();
		someInput.put("CHF 3000-5000 3'200.00", new LotPriceInfo(3000,5000,3200));
		someInput.put("CHF 600-840 - ", new LotPriceInfo(600,840,0));
		someInput.put("CHF 720-960 750.00", new LotPriceInfo(720,960, 750));
		someInput.put("CHF 360-480 450.00", new LotPriceInfo(360,480,450));
		someInput.put("CHF 7'800-9500 12'750.00", new LotPriceInfo(7800,9500,12750));
		someInput.put("CHF 10-50 99.00", new LotPriceInfo(10,50,99));
		someInput.put("CHF 3000-5000 3200.00", new LotPriceInfo(3000,5000,3200));
		someInput.put("CHF 600-840 -", new LotPriceInfo(600,840,0));
		
		
		for (Entry<String, LotPriceInfo> anElement : someInput.entrySet()) {
			LotPriceInfo processLotPricing = Wermuth2015ImportTask.processLotPricing(anElement.getKey());
			assertEquals(processLotPricing, anElement.getValue());
		}
		
	}

	@Test
	public void testNoOfBottles()
	{
		Map<Tuple2<String,String>,Integer> someInput = new HashMap<>();
		someInput.put(new Tuple2<>("1"," pro Dz. "), new Integer(12));
		someInput.put(new Tuple2<>("6"," pro Lot "), new Integer(6));
		someInput.put(new Tuple2<>("21"," pro Lot "), new Integer(21));
		someInput.put(new Tuple2<>("2"," pro Dutzend "), new Integer(24));
		someInput.put(new Tuple2<>("1"," pro dz. "), new Integer(1));
		someInput.put(new Tuple2<>("1"," pro Dz "), new Integer(12));
		
		for (Entry<Tuple2<String, String>, Integer> anElement : someInput.entrySet()) {
			int aNoOfBottles = Wermuth2015ImportTask.processNoOfBottles(anElement.getKey().getKey(), anElement.getKey().getValue());
			assertEquals(aNoOfBottles, anElement.getValue().intValue());
		}
	}

}
