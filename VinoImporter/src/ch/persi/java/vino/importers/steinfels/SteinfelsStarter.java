package ch.persi.java.vino.importers.steinfels;

import org.springframework.context.support.ClassPathXmlApplicationContext;

import ch.persi.java.vino.importers.ImportingStrategy;

public class SteinfelsStarter {

	/**
	 * @param args
	 */
	public static void main(String[] args) {
		
		try(ClassPathXmlApplicationContext classPathXmlApplicationContext = new ClassPathXmlApplicationContext("classpath:config.xml")) {
			ImportingStrategy steinfelsJob = (ImportingStrategy)classPathXmlApplicationContext.getBean("steinfelsImportJob");
			steinfelsJob.runImport();
		}
	}

}
