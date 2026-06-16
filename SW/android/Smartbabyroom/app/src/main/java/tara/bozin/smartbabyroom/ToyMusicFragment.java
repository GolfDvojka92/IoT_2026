package tara.bozin.smartbabyroom;

import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;

import org.json.JSONObject;

public class ToyMusicFragment extends Fragment
{

    private TextView tvToyState;
    private TextView tvMusicState;
    private Button btnToyToggle;
    private Button btnMusicToggle;
    private boolean toyOn = false;
    private boolean musicOn = false;
    private MQTTManager mqttManager;

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState)
    {
        View view = inflater.inflate(R.layout.fragment_toy_music, container, false);
        mqttManager = MQTTManager.getInstance();

        tvToyState = view.findViewById(R.id.tvToyState);
        tvMusicState = view.findViewById(R.id.tvMusicState);

        btnToyToggle = view.findViewById(R.id.btnToyToggle);
        btnMusicToggle = view.findViewById(R.id.btnMusicToggle);

        JSONObject state = mqttManager.getLastState();
        if (state != null)
        {
            updateFromState(state);
        }

        btnToyToggle.setOnClickListener(v -> toggleToy());
        btnMusicToggle.setOnClickListener(v -> toggleMusic());

        mqttManager.setParentStateListener(parentState ->
        {
            requireActivity().runOnUiThread(() ->
            {
                updateFromState(parentState);
            });
        });
        updateUi();
        return view;
    }

    private void toggleToy()
    {
        toyOn = !toyOn;
        if (toyOn)
        {
            mqttManager.publishParentCommand("TOY_ON");
        }
        else
        {
            mqttManager.publishParentCommand("TOY_OFF");
        }
        updateUi();
    }

    private void toggleMusic()
    {
        musicOn = !musicOn;
        if (musicOn)
        {
            mqttManager.publishParentCommand("MUSIC_ON");
        }
        else
        {
            mqttManager.publishParentCommand("MUSIC_OFF");
        }
        updateUi();
    }

    private void updateUi()
    {
        tvToyState.setText(toyOn ? "Toy: ON" : "Toy: OFF");
        btnToyToggle.setText(toyOn ? "Turn Toy OFF" : "Turn Toy ON");

        tvMusicState.setText(musicOn ? "Music: ON" : "Music: OFF");
        btnMusicToggle.setText(musicOn ? "Turn Music OFF" : "Turn Music ON");
    }

    private void updateFromState(JSONObject state)
    {
        String toy = state.optString("toy", "OFF");
        String music = state.optString("music", "OFF");

        toyOn = toy.equals("ON");
        musicOn = music.equals("ON");

        tvToyState.setText(getString(R.string.toy_state, toy));
        tvMusicState.setText(getString(R.string.music_state, music));

        btnToyToggle.setText(toyOn ? "Turn Toy OFF" : "Turn Toy ON");
        btnMusicToggle.setText(musicOn ? "Turn Music OFF" : "Turn Music ON");
    }
}