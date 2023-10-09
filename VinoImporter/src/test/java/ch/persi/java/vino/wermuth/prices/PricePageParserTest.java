package ch.persi.java.vino.wermuth.prices;

import java.io.IOException;
import java.util.Map;
import java.util.Map.Entry;

import org.codehaus.groovy.control.CompilationFailedException;
import org.junit.Test;

import ch.persi.java.vino.importers.wermuth.prices.HTMLPricePageExtractor;
import junit.framework.TestCase;

public class PricePageParserTest extends TestCase {

	
	@Test
	public void testGetByIndex() throws CompilationFailedException, InstantiationException, IllegalAccessException, IOException 
	{
		Map<Integer, Integer> extractPrices = new HTMLPricePageExtractor().extractPrices("test/resources/Weinauktion_WZ-219_Resultate.html");
		assertNotNull(extractPrices);
		assertTrue(extractPrices.size()==1404);
		
		for (Entry<Integer, Integer> aPriceRecord : extractPrices.entrySet()) {
			System.out.println("Lot Number: " +aPriceRecord.getKey()  + " price: " + aPriceRecord.getValue() );
		}
	}
	
	@Test
	public void testGetByPair() throws CompilationFailedException, InstantiationException, IllegalAccessException, IOException
	{
		Map<Integer, Integer> extractPrices = new HTMLPricePageExtractor().extractPrices("test/resources/Weinauktion_WZ-204_Resultate.html");
		assertNotNull(extractPrices);
		assertTrue(extractPrices.size()==924);
		
		for (Entry<Integer, Integer> aPriceRecord : extractPrices.entrySet()) {
			System.out.println("Lot Number: " +aPriceRecord.getKey()  + " price: " + aPriceRecord.getValue() );
		}
		
	}
}
