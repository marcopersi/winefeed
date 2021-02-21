package ch.persi.java.vino.importers.steinfels;

import ch.persi.java.vino.importers.ImportingStrategy;
import org.springframework.context.support.ClassPathXmlApplicationContext;

public class SteinfelsStarter {

	/**
	 * @param args a String array containing th parameters to adjust the Steinfels data extraction job
	 */
	public static void main(String[] args) {
		
		try(ClassPathXmlApplicationContext classPathXmlApplicationContext = new ClassPathXmlApplicationContext("classpath:config.xml")) {
			ImportingStrategy steinfelsJob = (ImportingStrategy)classPathXmlApplicationContext.getBean("steinfelsImportJob");
			steinfelsJob.runImport();
		}
	}

}
