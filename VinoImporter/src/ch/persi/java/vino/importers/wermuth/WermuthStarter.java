package ch.persi.java.vino.importers.wermuth;

import org.springframework.context.support.ClassPathXmlApplicationContext;

import ch.persi.java.vino.importers.ImportingStrategy;

public class WermuthStarter {

	/**
	 * @param theArguments
	 */
	public static void main(String[] theArguments) {
		try (ClassPathXmlApplicationContext aContext = new ClassPathXmlApplicationContext("classpath:config.xml"))
		{
			ImportingStrategy wermuthImport =(ImportingStrategy) aContext.getBean("wermuthImportJob");
	    	wermuthImport.runImport();
	    	aContext.close();
		}
	}

}
