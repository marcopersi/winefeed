package ch.persi.java.vino.config;

import ch.persi.java.vino.importers.Task;
import ch.persi.java.vino.importers.steinfels.SteinfelsImportTask;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.Configuration;

import java.util.HashSet;
import java.util.Set;

@Configuration
@ComponentScan(basePackages = "ch.persi.java.vino")
public class AppConfig {

    @Bean
    public Set<Task> steinfelsTasks(SteinfelsImportTask steinfelsImportTask) {
        Set<Task> tasks = new HashSet<>();
        tasks.add(steinfelsImportTask);
        return tasks;
    }
}