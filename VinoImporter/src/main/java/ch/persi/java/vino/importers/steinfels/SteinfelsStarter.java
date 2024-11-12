package ch.persi.java.vino.importers.steinfels;

import ch.persi.java.vino.config.AppConfig;
import ch.persi.java.vino.importers.ImportingStrategy;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.context.support.ClassPathXmlApplicationContext;

public class SteinfelsStarter {

    /**
     * @param args a String array containing th parameters to adjust the Steinfels data extraction job
     */
    public static void main(String[] args) {

        try (AnnotationConfigApplicationContext context = new AnnotationConfigApplicationContext(AppConfig.class)) {
            ImportingStrategy steinfelsJob = context.getBean(ImportingStrategy.class);
            steinfelsJob.runImport();
        }
    }






}
