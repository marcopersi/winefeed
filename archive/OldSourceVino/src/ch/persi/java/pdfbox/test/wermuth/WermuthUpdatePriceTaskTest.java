package ch.persi.java.pdfbox.test.wermuth;

import org.joda.time.DateTime;

import ch.persi.java.vino.importers.wermuth.WermuthUpdatePriceTask;
import junit.framework.TestCase;

public class WermuthUpdatePriceTaskTest extends TestCase {

	public void testIsWebPageAvailable()
	{
		WermuthUpdatePriceTask anUpdatePriceTask = new WermuthUpdatePriceTask("", new DateTime());
		anUpdatePriceTask.execute();
	}
	
}
