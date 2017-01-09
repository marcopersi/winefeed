package ch.persi.vino.steinfels;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;

import org.junit.Test;

import ch.persi.java.vino.importers.steinfels.NewRecordLineExtractor;
import ch.persi.java.vino.importers.steinfels.SteinfelsDateExtractingStrategy;
import ch.persi.java.vino.importers.steinfels.SteinfelsImportTask;
import junit.framework.TestCase;

public class SteinfelsTests extends TestCase {

	@Test
	public void testSuccessfullRecordLines()
	{
		List<String> someRecordLines = new ArrayList<>();
		someRecordLines.add("Château Le Fournas Bernadotte Haut Médoc 12 Flaschen OHK 1976 220 ");
		someRecordLines.add("Château Duhart Milon Pauillac 12 Flaschen OHK 1994 550 ");
		someRecordLines.add("Château Rauzan Gassies Margaux 12 Flaschen OHK 1981 830 ");
		someRecordLines.add("Château Croizet Bages Pauillac 12 Flaschen OHK 1983 11500 ");
		someRecordLines.add("Château Branaire Ducru Saint Julien 12 Flaschen OHK 1982 800 ");
		someRecordLines.add("Château Haut Brion Pessac Léognan 12 Flaschen OHK 1986 2'450 ");
		someRecordLines.add("Château La Lagune   Haut Médoc 2 Magnum 1977 140 ");
		someRecordLines.add("Masseto Tuscany 1 Doppelmagnum 2006 2500 ");
		someRecordLines.add("Masseto Tuscany 1 Impérial 6.0L 2006 2500 ");

		
		for (String aLine : someRecordLines) {
			boolean recordLine =new NewRecordLineExtractor(aLine).isRecordLine();
			System.out.println("Line: " + aLine + " is evaluated as: " + recordLine);
			assertTrue(recordLine);
		}
	}

	@Test
	public void testGetAuctionDate()
	{
		List<String> someLines = new ArrayList<>();
		someLines.add("Samstag, 4. Mai 2002 Ergebnisliste Steinfels Weinauktion, Löwenbräuareal, Limmatstrasse 264, 8005 Zürich");
		LocalDate aDate = new SteinfelsDateExtractingStrategy(someLines).getAuctionDate();
		assertNotNull(aDate);
		assertEquals(LocalDate.of(2002,5,4), aDate);
	}
	
	@Test
	public void testGetVintage()
	{
		Map<String, Integer> someRecordLines = new HashMap<>();
		someRecordLines.put("Château Duhart Milon Pauillac 2 Flaschen 1994 550 ", 1994);
		someRecordLines.put("Château Croizet Bages Pauillac 12 3/8 Flaschen OHK 1983 400 ",1983);
		someRecordLines.put("Château Le Fournas Bernadotte Haut Médoc 12 Flaschen OHK 2009 367 ", 2009);
		someRecordLines.put("Château Branaire Ducru Saint Julien 12 Flaschen OHK 1982 5000 ", 1982);
		someRecordLines.put("Château Haut Brion Pessac Léognan 12 Flaschen OHK 1986 12500 ", 1986);
		someRecordLines.put("Château La Lagune Haut Mé 2 Magnum 1977 12500 ", 1977);
		
		for (Entry<String, Integer> aLine : someRecordLines.entrySet()) {
			System.out.println("Vintage Evaluation Line: " + aLine.getKey());			
			assertEquals(aLine.getValue(), new NewRecordLineExtractor(aLine.getKey()).getVintage());
		}
	}

	@Test
	public void testGetPrice()
	{
		Map<String, Integer> someRecordLines = new HashMap<>();
		someRecordLines.put("Château Le Fournas Bernadotte Haut Médoc 12 Flaschen OHK 1976 220 ", 220);
		someRecordLines.put("Château Duhart Milon Pauillac 2 Flaschen 1994 1'550 ", 1550);
		someRecordLines.put("Château Croizet Bages Pauillac 12 3/8 Flaschen OHK 1983 750 ", 750);
		someRecordLines.put("Château Branaire Ducru Saint Julien 12 Flaschen OHK 1982 800 ", 800);
		someRecordLines.put("Château Haut Brion Pessac Léognan 12 Flaschen OHK 1986 2'450 ", 2450);
		someRecordLines.put("Château La Lagune   Haut Médoc 2 Magnum 1977 140 ", 140);
		
		for (Entry<String, Integer> aLine : someRecordLines.entrySet()) {
			System.out.println("Price evaluation: " + aLine.getKey());			
			assertEquals(aLine.getValue(), new NewRecordLineExtractor(aLine.getKey()).getRealizedPrice());
		}
	}
	
	@Test
	public void testSize()
	{
		Map<String, BigDecimal> someRecordLines = new HashMap<>();
		someRecordLines.put("Château Lafite Rothschild   Pauill 1 Flasche Impèriale 6,0Lt. 1979 1'400 ", BigDecimal.valueOf(60));
		for (Entry<String, BigDecimal> aLine : someRecordLines.entrySet()) {
			System.out.println("Size evaluation: " + aLine.getKey());			
			assertEquals(aLine.getValue(), new SteinfelsImportTask().getUnit(aLine.getKey()).getDeciliters());
		}
	}
	
}
