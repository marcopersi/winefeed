package ch.persi.java.vino.importers.weinboerse;

import org.springframework.context.support.ClassPathXmlApplicationContext;

import ch.persi.java.vino.importers.ImportingStrategy;

public class WeinboerseStarter {

	/**
	 * @param args
	 */
	public static void main(String[] args) {
		try (ClassPathXmlApplicationContext classPathXmlApplicationContext = new ClassPathXmlApplicationContext("classpath:config.xml"))
		{
			ImportingStrategy weinboerseJob = (ImportingStrategy)classPathXmlApplicationContext.getBean("weinboerseImportJob");
	    	weinboerseJob.runImport();
		}
	}

}
