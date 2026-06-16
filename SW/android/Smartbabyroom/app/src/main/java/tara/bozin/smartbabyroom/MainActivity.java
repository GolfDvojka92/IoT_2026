package tara.bozin.smartbabyroom;

import android.os.Bundle;
import android.widget.Button;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;
import androidx.fragment.app.Fragment;

public class MainActivity extends AppCompatActivity
{

    @Override
    protected void onCreate(Bundle savedInstanceState)
    {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        MQTTManager.getInstance().connect();

        Button btnToyMusic = findViewById(R.id.btnToyMusic);
        Button btnTemperature = findViewById(R.id.btnTemperature);
        Button btnLight = findViewById(R.id.btnLight);

        Button btnAuto = findViewById(R.id.btnAuto);
        TextView tvNotification = findViewById(R.id.tvNotification);
        TextView tvAlert = findViewById(R.id.tvAlert);

        btnAuto.setOnClickListener(v -> MQTTManager.getInstance().publishParentCommand("AUTO"));
        MQTTManager.getInstance().setNotificationListener((notification, alert) ->
                runOnUiThread(() ->
                {
                    tvNotification.setText(getString(R.string.notification_prefix, notification));
                    tvAlert.setText(getString(R.string.alert_prefix, alert));
                }));

        tvNotification.setText(getString(R.string.notification_prefix, MQTTManager.getInstance().getLastNotification()));
        tvAlert.setText(getString(R.string.alert_prefix, MQTTManager.getInstance().getLastAlert()));

        btnToyMusic.setOnClickListener(v -> openFragment(new ToyMusicFragment()));
        btnTemperature.setOnClickListener(v -> openFragment(new TemperatureFragment()));
        btnLight.setOnClickListener(v -> openFragment(new LightFragment()));

        if (savedInstanceState == null)
        {
            openFragment(new ToyMusicFragment());
        }
    }
    private void openFragment(Fragment fragment)
    {
        getSupportFragmentManager()
                .beginTransaction()
                .replace(R.id.fragmentContainer, fragment)
                .commit();
    }
}