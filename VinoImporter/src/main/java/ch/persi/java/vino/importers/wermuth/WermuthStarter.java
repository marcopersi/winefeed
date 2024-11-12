package ch.persi.java.vino.importers.wermuth;

import ch.persi.java.vino.importers.ImportingStrategy;
import org.springframework.context.support.ClassPathXmlApplicationContext;

public class WermuthStarter {

    /**
     * @param theArguments representing the required arguments in order to start an data import job for Wermuth S.A.
     */
    public static void main(String[] theArguments) {
        try (ClassPathXmlApplicationContext aContext = new ClassPathXmlApplicationContext("classpath:config.xml")) {
            ImportingStrategy wermuthImport = (ImportingStrategy) aContext.getBean("wermuthImportJob");
            wermuthImport.runImport();
        }
    }

}
